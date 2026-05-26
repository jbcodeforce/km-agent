import pytest
from pathlib import Path
from agno.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb
from agno.db.sqlite.sqlite import SqliteDb

from kma.tools.builder import build_linter_tools
from kma.db import build_default_embedder
from kma.agents.linter import build_linter_agent

import pathlib

data_dir = pathlib.Path(__file__).parent / "data"

"""
Test all linter agent related elements, like tools, prompt and agent response
"""

def create_test_knowledge() -> Knowledge:
    emb = build_default_embedder()
    vector_db = ChromaDb(
        name="test_vector_db",
        collection="test_collection",
        path= str(data_dir / "chroma"),
         embedder=emb,
    )
    contents_db = SqliteDb(db_file=str(data_dir / "contents.db"),
        knowledge_table= "test-km"
        )
    return Knowledge(
        name="k_test",
        vector_db=vector_db,
        contents_db=contents_db,
    )

def test_build_linter_tool():
    km_test = create_test_knowledge()
    results = build_linter_tools(knowledge = km_test)
    assert len(results) > 0
    for result in results:
        print(f"\n{result}")

def test_linter_agent():
    agent = build_linter_agent()
    assert agent