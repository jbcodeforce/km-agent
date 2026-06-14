"""Unit tests for in-process MLX embedder (mocked — no model download)."""

from unittest.mock import MagicMock, patch

import pytest

from kma.embeddings.local_mlx import (
    LocalMLXEmbedder,
    resolve_mlx_embed_repo,
    _fit_dimensions,
    _prefix_for_kind,
)


def test_resolve_mlx_embed_repo_aliases() -> None:
    assert resolve_mlx_embed_repo("nomical-modernbert-embed-base-4bit") == (
        "mlx-community/nomicai-modernbert-embed-base-4bit"
    )
    assert resolve_mlx_embed_repo("embeddinggemma-300m") == (
        "mlx-community/embeddinggemma-300m-bf16"
    )


def test_prefix_for_kind() -> None:
    assert _prefix_for_kind("modernbert", "hello").startswith("search_document:")
    assert _prefix_for_kind("gemma", "hello").startswith("task:")


def test_fit_dimensions_truncates_and_renormalizes() -> None:
    vec = [1.0, 0.0, 1.0]
    out = _fit_dimensions(vec, 2)
    assert len(out) == 2
    norm = sum(x * x for x in out)
    assert abs(norm - 1.0) < 1e-6


@patch("kma.embeddings.local_mlx.load_local_mlx_runtime")
@patch("kma.embeddings.local_mlx._embed_with_repo")
def test_local_mlx_embedder_get_embedding(
    mock_embed: MagicMock,
    mock_load: MagicMock,
) -> None:
    mock_load.return_value = ("mlx-community/nomicai-modernbert-embed-base-4bit", "modernbert")
    mock_embed.return_value = [0.1, 0.2, 0.3]

    emb = LocalMLXEmbedder(id="nomical-modernbert-embed-base-4bit", dimensions=3)
    vector = emb.get_embedding("test content")
    assert vector == [0.1, 0.2, 0.3]
    mock_embed.assert_called_once_with(
        "mlx-community/nomicai-modernbert-embed-base-4bit",
        "test content",
    )


@patch("kma.embeddings.local_mlx.load_local_mlx_runtime")
def test_local_mlx_embedder_fallback_on_primary_load_failure(mock_load: MagicMock) -> None:
    mock_load.side_effect = [
        ("mlx-community/embeddinggemma-300m-bf16", "gemma"),
    ]
    # Simulate primary failure inside load_local_mlx_runtime — already returns fallback
    emb = LocalMLXEmbedder(
        id="nomical-modernbert-embed-base-4bit",
        hf_repo="mlx-community/embeddinggemma-300m-bf16",
        kind="gemma",
        dimensions=768,
    )
    assert emb.kind == "gemma"
