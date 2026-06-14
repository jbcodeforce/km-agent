"""In-process MLX embedding models (no OMLX / HTTP embed server)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from agno.knowledge.embedder.base import Embedder
from agno.utils.log import log_warning

MlxEmbedKind = Literal["modernbert", "gemma"]

# User-facing ids → Hugging Face MLX repos
_MLX_REPO_ALIASES: dict[str, str] = {
    "nomical-modernbert-embed-base-4bit": "mlx-community/nomicai-modernbert-embed-base-4bit",
    "nomicai-modernbert-embed-base-4bit": "mlx-community/nomicai-modernbert-embed-base-4bit",
    "mlx-community/nomicai-modernbert-embed-base-4bit": "mlx-community/nomicai-modernbert-embed-base-4bit",
    "embeddinggemma-300m": "mlx-community/embeddinggemma-300m-bf16",
    "embeddinggemma-300m-6bit": "mlx-community/embeddinggemma-300m-bf16",
    "mlx-community/embeddinggemma-300m-bf16": "mlx-community/embeddinggemma-300m-bf16",
}

_DEFAULT_PRIMARY_MODEL = "nomical-modernbert-embed-base-4bit"
_DEFAULT_FALLBACK_MODEL = "embeddinggemma-300m"

# Loaded once per process per repo: (model, processor/tokenizer, kind)
_MLX_RUNTIME_CACHE: dict[str, tuple[Any, Any, MlxEmbedKind]] = {}


def resolve_mlx_embed_repo(model_id: str) -> str:
    """Map a configured model id to an ``mlx-community/...`` repo."""
    key = model_id.strip()
    if key in _MLX_REPO_ALIASES:
        return _MLX_REPO_ALIASES[key]
    if "/" in key:
        return key
    raise ValueError(
        f"Unknown local MLX embed model {model_id!r}; "
        f"expected one of {sorted(_MLX_REPO_ALIASES)} or a Hugging Face repo id"
    )


def _infer_kind(hf_repo: str) -> MlxEmbedKind:
    lower = hf_repo.lower()
    if "gemma" in lower or "embeddinggemma" in lower:
        return "gemma"
    return "modernbert"


def _prefix_for_kind(kind: MlxEmbedKind, text: str) -> str:
    stripped = text.strip()
    if kind == "gemma":
        if stripped.startswith("task:"):
            return stripped
        return f"task: search result | query: {stripped}"
    if stripped.startswith("search_query:") or stripped.startswith("search_document:"):
        return stripped
    return f"search_document: {stripped}"


def _fit_dimensions(vector: List[float], dimensions: int) -> List[float]:
    if dimensions <= 0:
        raise ValueError(f"dimensions must be positive, got {dimensions}")
    if len(vector) < dimensions:
        log_warning(
            f"Embedding length {len(vector)} is smaller than configured dimensions {dimensions}"
        )
        return []
    truncated = vector[:dimensions]
    if dimensions < len(vector):
        norm = math.sqrt(sum(x * x for x in truncated))
        if norm > 0:
            truncated = [x / norm for x in truncated]
    return truncated


def _vector_from_mlx_array(arr: Any) -> List[float]:
    if hasattr(arr, "tolist"):
        raw = arr.tolist()
    else:
        raw = list(arr)
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        return [float(x) for x in raw[0]]
    return [float(x) for x in raw]


def _load_runtime(hf_repo: str) -> tuple[Any, Any, MlxEmbedKind]:
    if hf_repo in _MLX_RUNTIME_CACHE:
        return _MLX_RUNTIME_CACHE[hf_repo]

    from mlx_embeddings import load

    kind = _infer_kind(hf_repo)
    model, processor = load(hf_repo)
    _MLX_RUNTIME_CACHE[hf_repo] = (model, processor, kind)
    return model, processor, kind


def _embed_with_repo(hf_repo: str, text: str) -> List[float]:
    model, processor, kind = _load_runtime(hf_repo)
    prefixed = _prefix_for_kind(kind, text)

    if kind == "modernbert":
        from mlx_embeddings import generate

        output = generate(model, processor, texts=[prefixed])
        return _vector_from_mlx_array(output.text_embeds)

    encoded = processor(
        [prefixed],
        padding=True,
        truncation=True,
        return_tensors="mlx",
    )
    output = model(encoded["input_ids"], encoded["attention_mask"])
    return _vector_from_mlx_array(output.text_embeds)


def load_local_mlx_runtime(primary_model_id: str, fallback_model_id: str) -> tuple[str, MlxEmbedKind]:
    """Load primary MLX embed repo, falling back to ``fallback_model_id`` on failure."""
    primary_repo = resolve_mlx_embed_repo(primary_model_id)
    try:
        _, _, kind = _load_runtime(primary_repo)
        return primary_repo, kind
    except Exception as primary_err:
        fallback_repo = resolve_mlx_embed_repo(fallback_model_id)
        log_warning(
            f"Failed to load MLX embed model {primary_repo}: {primary_err}; "
            f"falling back to {fallback_repo}"
        )
        _, _, kind = _load_runtime(fallback_repo)
        return fallback_repo, kind


@dataclass
class LocalMLXEmbedder(Embedder):
    """Agno embedder backed by ``mlx-embeddings`` in the current Python process."""

    id: str = _DEFAULT_PRIMARY_MODEL
    hf_repo: str = ""
    kind: MlxEmbedKind = "modernbert"
    dimensions: Optional[int] = 768
    fallback_model_id: str = _DEFAULT_FALLBACK_MODEL

    def __post_init__(self) -> None:
        if self.enable_batch:
            log_warning("LocalMLXEmbedder does not support batch embeddings; enable_batch=False")
            self.enable_batch = False
        if not self.hf_repo:
            self.hf_repo, self.kind = load_local_mlx_runtime(self.id, self.fallback_model_id)

    def get_embedding(self, text: str) -> List[float]:
        try:
            vector = _embed_with_repo(self.hf_repo, text)
            return _fit_dimensions(vector, self.dimensions or len(vector))
        except Exception as e:
            log_warning(f"Local MLX embedding failed: {e}")
            return []

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        return self.get_embedding(text), None

    async def async_get_embedding(self, text: str) -> List[float]:
        return self.get_embedding(text)

    async def async_get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        return self.get_embedding_and_usage(text)
