"""Unit tests for studies code → wiki catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from kma.code_catalog import (
    IntentSummary,
    LabPack,
    build_lab_pack,
    discover_code_root,
    extract_blurb_from_readme,
    fallback_intent,
    iter_categories,
    iter_labs,
    merge_code_catalogs_into_index,
    render_category_page,
    write_code_catalog,
    CategoryCatalog,
)

ROOT = Path(__file__).resolve().parents[1]
STUDIES_FIXTURE = ROOT / "data" / "studies-code"


def test_discover_code_root() -> None:
    root = discover_code_root(STUDIES_FIXTURE)
    assert root.name == "code"
    assert (root / "flink-sql").is_dir()


def test_iter_categories_and_labs() -> None:
    code = discover_code_root(STUDIES_FIXTURE)
    cats = iter_categories(code)
    assert any(c.name == "flink-sql" for c in cats)
    labs = iter_labs(code / "flink-sql")
    names = {p.name for p in labs}
    assert "00-basic-sql" in names
    assert "04-joins" in names


def test_extract_blurb_prefers_section() -> None:
    text = "# Cat\n\nIntro.\n\n## 04-joins\n\nJoin blurbs here.\n\n## Other\n\nNope.\n"
    assert "Join blurbs" in extract_blurb_from_readme(text, "04-joins")


def test_build_lab_pack_has_sql() -> None:
    pack = build_lab_pack(
        STUDIES_FIXTURE / "code" / "flink-sql" / "04-joins",
        STUDIES_FIXTURE,
    )
    assert pack.rel_path == "code/flink-sql/04-joins"
    assert any(f.endswith(".sql") or f.endswith("deploy_manifest.json") for f in pack.notable_files)
    assert "join" in pack.readme_excerpt.lower() or "Join" in pack.readme_excerpt


def test_merge_code_catalogs_section(tmp_path: Path) -> None:
    index = tmp_path / "index.md"
    index.write_text("# Wiki Index\n\n## Concepts\n- [A](wiki/concepts/a.md) — a\n", encoding="utf-8")
    merge_code_catalogs_into_index(
        index,
        [("Code: Flink Sql", "wiki/concepts/code-flink-sql.md", "SQL labs")],
    )
    text = index.read_text(encoding="utf-8")
    assert "## Concepts" in text
    assert "## Code catalogs" in text
    assert "code-flink-sql.md" in text
    # Second merge replaces section
    merge_code_catalogs_into_index(
        index,
        [("Code: Dbt", "wiki/concepts/code-dbt.md", "dbt projects")],
    )
    text2 = index.read_text(encoding="utf-8")
    assert "code-dbt.md" in text2
    assert text2.count("## Code catalogs") == 1
    assert "code-flink-sql.md" not in text2


def test_write_code_catalog_no_llm(tmp_path: Path) -> None:
    ctx = tmp_path / "context"
    stats = write_code_catalog(
        ctx,
        STUDIES_FIXTURE,
        use_llm=False,
        force=True,
    )
    assert stats.categories >= 1
    assert stats.labs >= 1
    assert stats.written >= 1
    page = ctx / "wiki" / "concepts" / "code-flink-sql.md"
    assert page.is_file()
    body = page.read_text(encoding="utf-8")
    assert "code:" in body
    assert "code/flink-sql/" in body
    assert "<!-- kma-pack-hash:" in body
    index = (ctx / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "## Code catalogs" in index
    assert "code-flink-sql.md" in index


def test_write_skips_unchanged_without_force(tmp_path: Path) -> None:
    ctx = tmp_path / "context"
    write_code_catalog(ctx, STUDIES_FIXTURE, use_llm=False, force=True)
    stats2 = write_code_catalog(ctx, STUDIES_FIXTURE, use_llm=False, force=False)
    assert stats2.skipped_unchanged >= 1
    assert stats2.written == 0


def test_write_with_mock_summarize(tmp_path: Path) -> None:
    ctx = tmp_path / "context"

    def fake_summarize(pack: LabPack) -> IntentSummary:
        return IntentSummary(
            intent=f"INTENT for {pack.name}: teaches streaming concepts.",
            tags=("flink", "sql"),
        )

    stats = write_code_catalog(
        ctx,
        STUDIES_FIXTURE,
        use_llm=True,
        force=True,
        summarize=fake_summarize,
    )
    assert stats.llm_calls >= 1
    body = (ctx / "wiki" / "concepts" / "code-flink-sql.md").read_text(encoding="utf-8")
    assert "INTENT for" in body
    assert "flink" in body.lower()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    ctx = tmp_path / "context"
    stats = write_code_catalog(ctx, STUDIES_FIXTURE, dry_run=True, use_llm=False)
    assert stats.labs >= 1
    assert not (ctx / "wiki" / "concepts").exists()


def test_render_includes_code_frontmatter() -> None:
    pack = LabPack(
        rel_path="code/flink-sql/00-basic-sql",
        name="00-basic-sql",
        readme_excerpt="Basic lab",
        notable_files=("code/flink-sql/00-basic-sql/README.md",),
    )
    catalog = CategoryCatalog(
        name="flink-sql",
        rel_path="code/flink-sql",
        intro="Flink SQL category",
        labs=[(pack, fallback_intent(pack))],
    )
    text = render_category_page(catalog, pack_hash="abc123")
    assert 'title: "Code: Flink Sql"' in text or "Code: Flink" in text
    assert "code/flink-sql/00-basic-sql" in text
    assert "kma-pack-hash: abc123" in text


def test_discover_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        discover_code_root(tmp_path)
