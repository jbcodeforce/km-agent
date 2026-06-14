
from agno.knowledge import Knowledge
from agno.tools import tool


def create_update_knowledge(knowledge: Knowledge):
    """Create an update_knowledge tool bound to a specific knowledge base.

    The returned tool lets the agent save metadata (file manifests, schema
    index entries, source capabilities, discoveries) to the knowledge base.

    Args:
        knowledge: The Knowledge instance to insert into.

    Returns:
        A tool function that the agent can call.
    """

    @tool
    def update_knowledge(title: str, content: str) -> str:
        """Save metadata to the knowledge base.

        Use this to record structural information about KMA's context graph:
        - File manifests: what files exist and what they contain
        - Schema index: what SQL tables exist and their structure
        - Source capabilities: what tools are available
        - Discoveries: where information was found for specific topics
        - Wiki articles: what compiled articles exist
        - Raw sources: what ingested documents exist

        Args:
            title: A descriptive title prefixed with its category
            content: The metadata content describing the resource —
                columns, purpose, location, tags, etc.

        Returns:
            Confirmation message.
        """
        knowledge.insert(name=title, text_content=content)
        return f"Knowledge updated: {title}"

    return update_knowledge


def create_search_wiki(wiki_knowledge: Knowledge):
    """Create search_wiki tool for semantic recall over embedded wiki chunks."""

    @tool
    def search_wiki(query: str, max_results: int = 8) -> str:
        """Semantic search over offline-indexed wiki articles (pgvector).

        Use after wiki content has been embedded via ``scripts/index_wiki.py``.
        Returns relevant excerpts with wiki paths; follow up with ``read_file``
        for full articles when needed.

        Args:
            query: Natural language search query.
            max_results: Maximum chunks to return (default 8).

        Returns:
            Matching wiki excerpts or a message when nothing is found.
        """
        docs = wiki_knowledge.search(query, max_results=max_results)
        if not docs:
            return "No wiki matches found. Try read_wiki_index and read_file, or re-run index_wiki."
        parts: list[str] = []
        for i, doc in enumerate(docs, start=1):
            meta = doc.meta_data or {}
            path = meta.get("wiki_path", meta.get("name", "unknown"))
            content = (doc.content or "").strip()
            if len(content) > 1200:
                content = content[:1200] + "..."
            parts.append(f"### {i}. {path}\n{content}")
        return "\n\n".join(parts)

    return search_wiki