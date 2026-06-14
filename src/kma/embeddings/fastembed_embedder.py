"""In-process CPU embeddings via fastembed (Docker-friendly)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from agno.knowledge.embedder.base import Embedder
from agno.utils.log import log_warning

_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"

_RUNTIME_CACHE: dict[str, Any] = {}


def _load_text_embedding(model_name: str) -> Any:
    if model_name in _RUNTIME_CACHE:
        return _RUNTIME_CACHE[model_name]
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=model_name)
    _RUNTIME_CACHE[model_name] = model
    return model


@dataclass
class FastEmbedEmbedder(Embedder):
    """Agno embedder backed by ``fastembed`` in the current Python process."""

    id: str = _DEFAULT_MODEL
    dimensions: Optional[int] = 384
    _model: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.enable_batch:
            log_warning("FastEmbedEmbedder batch mode not customized; using single-text embed")
            self.enable_batch = False

    def _ensure_model(self) -> Any:
        if self._model is None:
            self._model = _load_text_embedding(self.id)
        return self._model

    def _vector_from_result(self, result: Any) -> List[float]:
        if hasattr(result, "tolist"):
            return result.tolist()
        return list(result)

    def get_embedding(self, text: str) -> List[float]:
        try:
            model = self._ensure_model()
            batch = list(model.embed([text]))
            if not batch:
                return []
            vector = self._vector_from_result(batch[0])
            if self.dimensions and len(vector) > self.dimensions:
                vector = vector[: self.dimensions]
            return vector
        except Exception as e:
            log_warning(f"FastEmbed embedding failed: {e}")
            return []

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        return self.get_embedding(text), None

    async def async_get_embedding(self, text: str) -> List[float]:
        return self.get_embedding(text)

    async def async_get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        return self.get_embedding_and_usage(text)
