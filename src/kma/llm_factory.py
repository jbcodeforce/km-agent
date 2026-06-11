"""Construct default Agno chat models for the Compiler from environment."""

from __future__ import annotations

from agno.models.base import Model
from agno.models.ollama import OllamaResponses
from agno.models.openai import OpenAIResponses, OpenAILike
from agno.knowledge.embedder.base import Embedder
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.knowledge.embedder.openai import OpenAIEmbedder

from kma.config import (
    Env,
    get_llm_model_id,
    get_llm_provider,
    get_llm_api_key,
    get_llm_base_url,
    get_embed_provider,
    get_embed_model_id,
    get_embed_dimensions,
    get_embed_base_url,
    get_embed_host
)

def build_default_llm_model() -> Model:
    """Return the LLM chat model for ``KMA_LLM_PROVIDER``."""
    provider = get_llm_provider()
    mid = get_llm_model_id()
    api_key = get_llm_api_key()
    base_url = get_llm_base_url()
    if provider == "ollama":
        return OllamaResponses(id=mid, base_url=base_url)

    if provider == "openai":
        base_url = base_url.strip() if base_url and base_url.strip() else None
        return OpenAIResponses(id=mid, api_key=api_key.strip(), base_url=base_url)

    if provider == "mlx":
        return OpenAILike(
            id=mid,
            base_url=base_url,
            api_key=api_key,
        )

    # anthropic
    from agno.models.anthropic import Claude
    if not api_key or not api_key.strip():
        raise ValueError(
            f"{Env.KMA_LLM_API_KEY} is required when {Env.KMA_LLM_PROVIDER}=anthropic "
            "(set the key in the environment or .env)"
        )
    return Claude(id=mid, api_key=api_key.strip())



def build_default_embedder() -> Embedder:
    """Embedder for Knowledge bases from ``KMA_EMBED_PROVIDER``."""
    provider = get_embed_provider()
    api_key = get_llm_api_key()
    model_id = get_embed_model_id()
    dimensions = get_embed_dimensions()
    if provider == "ollama":
        return OllamaEmbedder(
            id=model_id,
            host=get_embed_host(),
            dimensions=dimensions,
        )
    if provider == "mlx":
        return OpenAIEmbedder(
            id=model_id,
            dimensions=dimensions,
            api_key=api_key,
            base_url=get_embed_base_url(),
        )
    # openai
    return OpenAIEmbedder(
        id=model_id,
        dimensions=dimensions,
        api_key=api_key,
        base_url=get_embed_base_url(),
    )
