
from agno.db.postgres import PostgresDb
from agno.knowledge import Knowledge
from agno.knowledge.embedder.base import Embedder
from agno.vectordb.pgvector import PgVector, SearchType
from sqlalchemy import Engine, create_engine, text
from os import getenv
from urllib.parse import quote
from kma.llm_factory import build_default_embedder
from kma.config import (
    Env
)


def build_db_url() -> str:
    """Build database URL from environment variables.

    Reads ``KMA_DB_*`` first, then ``DB_*`` (legacy), then defaults.
    """
    driver =  "postgresql+psycopg"
    user = getenv(Env.KMA_DB_USER, "ai")
    password = quote(getenv(Env.KMA_DB_PASS, "ai"), safe="")
    host = getenv(Env.KMA_DB_HOST, "localhost")
    port = getenv(Env.KMA_DB_PORT, "5432")
    database = getenv(Env.KMA_DB_DATABASE, "ai")

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
