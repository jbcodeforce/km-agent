import pytest
import pathlib

data_dir = pathlib.Path(__file__).parent.parent / "data"
from kma.tools.wiki import get_or_create_wiki_paths, create_wiki_tools

def test_wiki_folders():
    context_dir = data_dir / "context"
    ctx, docs, wiki = get_or_create_wiki_paths(context_dir)
    assert ctx
    assert docs
    assert wiki
    assert wiki / "raw"

    tools = create_wiki_tools(wiki)
    assert tools
    assert len(tools) >= 4