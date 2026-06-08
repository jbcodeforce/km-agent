"""DEVELOPER_PRACTICES documents the OMLX integration suite."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = REPO_ROOT / "docs" / "DEVELOPER_PRACTICES.md"


def test_doc_mentions_omlx_and_gate() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "OMLX" in text
    assert "KMA_IT_MLX" in text
    assert "KMA_MLX_BASE_URL" in text
