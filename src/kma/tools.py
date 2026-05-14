



def build_compiler_tools(knowledge: Knowledge) -> list:
    """Tools for the Compiler agent — reads raw/, writes wiki/."""
    _, _, read_manifest, update_compiled = create_ingest_tools(RAW_DIR)
    return [
        FileTools(base_dir=KMA_CONTEXT_DIR, enable_delete_file=False),
        create_update_knowledge(knowledge),
        read_manifest,
        update_compiled,
        *create_wiki_tools(WIKI_DIR),
    ]