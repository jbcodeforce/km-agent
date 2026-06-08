
from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.base import Embedder
from agno.knowledge.embedder.ollama import OllamaEmbedder
from agno.knowledge.embedder.openai import OpenAIEmbedder
from agno.vectordb.pgvector import PgVector, SearchType
from sqlalchemy import Engine, create_engine, text
from os import getenv
from urllib.parse import quote

from kma.config import (
    get_embed_base_url,
    get_embed_dimensions,
    get_embed_model_id,
    get_embed_provider,
    get_mlx_api_key,
    get_mlx_embed_base_url,
    get_ollama_embed_host,
)


def _env_db(kma_key: str, legacy_key: str, default: str) -> str:
    """Prefer ``KMA_*`` names; fall back to legacy ``DB_*`` for backward compatibility."""
    v = getenv(kma_key)
    if v is not None and str(v).strip() != "":
        return v
    v2 = getenv(legacy_key)
    if v2 is not None and str(v2).strip() != "":
        return v2
    return default


def build_db_url() -> str:
    """Build database URL from environment variables.

    Reads ``KMA_DB_*`` first, then ``DB_*`` (legacy), then defaults.
    """
    driver = _env_db("KMA_DB_DRIVER", "DB_DRIVER", "postgresql+psycopg")
    user = _env_db("KMA_DB_USER", "DB_USER", "ai")
    password = quote(_env_db("KMA_DB_PASS", "DB_PASS", "ai"), safe="")
    host = _env_db("KMA_DB_HOST", "DB_HOST", "localhost")
    port = _env_db("KMA_DB_PORT", "DB_PORT", "5432")
    database = _env_db("KMA_DB_DATABASE", "DB_DATABASE", "ai")

    return f"{driver}://{user}:{password}@{host}:{port}/{database}"

db_url = build_db_url()
DB_ID = "kma-db"
KMA_SCHEMA = "kma"

def get_postgres_db(contents_table: str | None = None) -> PostgresDb:
    """Create a PostgresDb instance.

    Args:
        contents_table: Optional table name for storing knowledge contents.

    Returns:
        Configured PostgresDb instance.
    """
    if contents_table is not None:
        return PostgresDb(id=DB_ID, db_url=db_url, knowledge_table=contents_table)
    return PostgresDb(id=DB_ID, db_url=db_url)


def build_default_embedder() -> Embedder:
    """Embedder for Knowledge bases from ``KMA_EMBED_PROVIDER``."""
    provider = get_embed_provider()
    if provider == "ollama":
        return OllamaEmbedder(
            id=get_embed_model_id(),
            host=get_ollama_embed_host(),
            dimensions=get_embed_dimensions(),
        )
    if provider == "mlx":
        return OpenAIEmbedder(
            id=get_embed_model_id(),
            dimensions=get_embed_dimensions(),
            api_key=get_mlx_api_key(),
            base_url=get_mlx_embed_base_url(),
        )
    # openai
    api_key = getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "OPENAI_API_KEY is required when KMA_EMBED_PROVIDER=openai "
            "(set the key in the environment or .env)"
        )
    return OpenAIEmbedder(
        id=get_embed_model_id(),
        dimensions=get_embed_dimensions(),
        api_key=api_key.strip(),
        base_url=get_embed_base_url(),
    )


def create_knowledge(name: str, table_name: str, embedder: Embedder | None = None) -> Knowledge:
    """Create a Knowledge instance with PgVector hybrid search.

    Args:
        name: Display name for the knowledge base.
        table_name: PostgreSQL table name for vector storage.
        embedder: Optional custom embedder (defaults from ``KMA_EMBED_PROVIDER`` / config).

    Returns:
        Configured Knowledge instance.
    """
    emb = embedder or build_default_embedder()
    return Knowledge(
        name=name,
        vector_db=PgVector(
            db_url=db_url,
            table_name=table_name,
            search_type=SearchType.hybrid,
            embedder=emb,
        ),
        contents_db=get_postgres_db(contents_table=f"{table_name}_contents"),
    )


def get_sql_engine() -> Engine:
    bootstrap = create_engine(db_url)
    with bootstrap.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {KMA_SCHEMA}"))
        conn.commit()
    bootstrap.dispose()
    return create_engine(
        db_url,
        connect_args={"options": f"-c search_path={KMA_SCHEMA},public"},
    )
