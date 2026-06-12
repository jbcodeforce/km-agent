"""Unit tests for compile prompt helpers."""

from __future__ import annotations

from kma.agents.compiler import (
    build_compile_file_prompt,
    compile_file_read_path,
    compile_summary_basename,
)


def test_compile_file_read_path_single_root() -> None:
    assert compile_file_read_path("fitforpurpose.md") == "raw/fitforpurpose.md"


def test_compile_file_read_path_labelled() -> None:
    assert compile_file_read_path("studies:sql/joins.md") == "raw/studies/sql/joins.md"


def test_compile_summary_basename() -> None:
    assert compile_summary_basename("fitforpurpose.md") == "fitforpurpose.md"
    assert compile_summary_basename("studies:kafka.md") == "kafka.md"


def test_build_compile_file_prompt_names_single_file() -> None:
    prompt = build_compile_file_prompt("fitforpurpose.md")
    assert "fitforpurpose.md" in prompt
    assert "raw/fitforpurpose.md" in prompt
    assert "Do not compile any other uncompiled" in prompt
    assert "process every entry" not in prompt.lower()
    assert "compiled is false" not in prompt.lower() or "confirm fitforpurpose.md has compiled false" in prompt


def test_build_compile_file_prompt_labelled_id() -> None:
    prompt = build_compile_file_prompt("studies:kafka.md", automated=True)
    assert "studies:kafka.md" in prompt
    assert "raw/studies/kafka.md" in prompt
    assert "wiki/summaries/kafka.md" in prompt
    assert "automated compile" in prompt.lower()
    assert "Do not compile any other uncompiled" in prompt
