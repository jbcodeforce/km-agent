"""The tests/data raw corpus exists and carries valid raw frontmatter."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW = REPO_ROOT / "tests" / "data" / "raw"


def test_corpus_has_several_markdown_files() -> None:
    files = sorted(RAW.glob("*.md"))
    assert len(files) >= 4, f"expected >=4 seed docs, found {len(files)}"


def test_each_doc_has_yaml_frontmatter() -> None:
    for f in sorted(RAW.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{f.name} missing frontmatter open"
        assert "\n---\n" in text, f"{f.name} missing frontmatter close"
        assert "title:" in text.split("\n---\n", 1)[0], f"{f.name} missing title"
