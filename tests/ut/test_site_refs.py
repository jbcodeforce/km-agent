"""Unit tests for web_site_ref.json loading and formatting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kma.tools.site_refs import (
    WebSiteRef,
    format_site_refs_for_prompt,
    load_site_refs_for_context,
    load_web_site_refs,
    resolve_site_refs_path,
)


def test_load_web_site_refs_array(tmp_path: Path) -> None:
    path = tmp_path / "refs.json"
    path.write_text(
        json.dumps(
            [
                {
                    "name": "Example",
                    "url": "https://example.com",
                    "description": "Test source",
                }
            ]
        )
    )
    refs = load_web_site_refs(path)
    assert refs == [WebSiteRef("Example", "https://example.com", "Test source")]


def test_load_web_site_refs_sites_wrapper(tmp_path: Path) -> None:
    path = tmp_path / "refs.json"
    path.write_text(
        json.dumps(
            {
                "sites": [
                    {
                        "name": "A",
                        "url": "https://a.test",
                        "description": "First",
                    }
                ]
            }
        )
    )
    refs = load_web_site_refs(path)
    assert len(refs) == 1
    assert refs[0].name == "A"


def test_load_web_site_refs_missing_field(tmp_path: Path) -> None:
    path = tmp_path / "refs.json"
    path.write_text(json.dumps([{"name": "X", "url": "https://x.test"}]))
    with pytest.raises(ValueError, match="description"):
        load_web_site_refs(path)


def test_load_web_site_refs_invalid_shape(tmp_path: Path) -> None:
    path = tmp_path / "refs.json"
    path.write_text(json.dumps({"foo": []}))
    with pytest.raises(ValueError, match="array"):
        load_web_site_refs(path)


def test_format_site_refs_for_prompt() -> None:
    text = format_site_refs_for_prompt(
        [WebSiteRef("Flink", "https://flink.apache.org", "Official docs")]
    )
    assert "Flink" in text
    assert "https://flink.apache.org" in text
    assert "Official docs" in text


def test_format_site_refs_empty() -> None:
    assert format_site_refs_for_prompt([]) == ""


def test_resolve_site_refs_path_explicit(tmp_path: Path) -> None:
    explicit = tmp_path / "custom.json"
    explicit.write_text("[]")
    resolved = resolve_site_refs_path(tmp_path, explicit)
    assert resolved == explicit.resolve()


def test_resolve_site_refs_path_default(tmp_path: Path) -> None:
    default = tmp_path / "web_site_ref.json"
    default.write_text("[]")
    assert resolve_site_refs_path(tmp_path, None) == default.resolve()
    assert resolve_site_refs_path(tmp_path / "missing", None) is None


def test_load_site_refs_for_context_fixture() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    refs = load_site_refs_for_context(data_dir, data_dir / "web_site_ref.json")
    assert len(refs) >= 2
    assert any("Flink" in r.name for r in refs)
