"""example.env documents the OMLX (`mlx`) provider knobs."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_ENV = REPO_ROOT / "example.env"


def test_example_env_documents_mlx() -> None:
    text = EXAMPLE_ENV.read_text(encoding="utf-8")
    for token in (
        "KMA_LLM_PROVIDER=mlx",
        "KMA_MLX_BASE_URL",
        "KMA_MLX_API_KEY",
        "KMA_EMBED_PROVIDER=mlx",
        "KMA_EMBED_MODEL",
        "KMA_EMBED_DIMENSIONS",
    ):
        assert token in text, f"missing {token!r} in example.env"
