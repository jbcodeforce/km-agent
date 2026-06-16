# KMA agent tools

Agno `@tool` functions and factories used by KMA agents. Tools read and write under the **context directory** (`KMA_CONTEXT_DIR`): mainly `wiki/` (compiled articles) and `raw/` (ingested sources).

Agent-specific bundles are assembled in `builder.py`.

## Layout on disk

| Path | Role |
|------|------|
| `wiki/` | Compiled markdown articles, `index.md`, `.state.json` |
| `wiki/index.md` | Table of contents / summaries for compiled articles |
| `wiki/.state.json` | Last compile/lint timestamps and counts |
| `raw/` | Source documents (markdown + YAML frontmatter) |
| `raw/.manifest.json` | Index of ingested files and `compiled` flags |

The Compiler may use **multiple raw roots** on disk; agents then see virtual paths `raw/<label>/...` (see `compiler_fs.py`).

## Modules

### `builder.py`

**Intent:** Single place to build the tool list each agent receives.

| Function | Agent | Tools included (summary) |
|----------|-------|---------------------------|
| `build_compiler_tools` | Compiler | File I/O (wiki + raw), `update_knowledge`, manifest read/update, full wiki tools |
| `build_navigator_tools` | Navigator | SQL, files, `update_knowledge`, read-only wiki index/state, `read_manifest` |
| `build_researcher_tools` | Researcher | Files, Parallel search/extract, `update_knowledge`, `read_web_site_refs`, ingest + manifest |
| `build_linter_tools` | Linter | Files, `update_knowledge`, wiki index/state (read + update state) |
| `build_team_tools` | kma team leader | `trigger_wiki_refresh` — background compile + lint after research ingest |

### `wiki.py`

**Intent:** Manage wiki metadata agents need without scanning every article file.

- `read_wiki_index` / `update_wiki_index` — `wiki/index.md`
- `read_wiki_state` / `update_wiki_state` — `wiki/.state.json` (compile/lint timestamps, counts)

Used by Compiler (read/write), Navigator and Linter (mostly read; Linter updates state after lint).

### `knowledge.py`

**Intent:** Persist **structural metadata** in the Agno vector knowledge base (manifests, schema notes, discoveries), not full article bodies.

- `create_update_knowledge(knowledge)` → `update_knowledge(title, content)` — `knowledge.insert(...)`

Shared by Compiler, Navigator, Researcher, and Linter.

### `ingest.py`

**Intent:** Bring **external content into `raw/`** and track what still needs compilation.

- `ingest_url` — Fetch URL (Parallel when configured), save markdown + frontmatter, append manifest
- `ingest_text` — Save user/research text as a raw markdown file
- `read_manifest` — List ingested files and `compiled` status
- `update_manifest_compiled` — Mark a source as compiled after wiki work
- `sync_raw_manifest_from_disk` — Rebuild manifest from existing `*.md` frontmatter

`create_compiler_manifest_tools` merges manifests across **multiple raw roots** for the Compiler (`file_id` as `label:relpath` when needed).

### `site_refs.py`

**Intent:** Load trusted web sources from `web_site_ref.json` for research bias.

- `load_web_site_refs(path)` — parse JSON array or `{"sites": [...]}`
- `format_site_refs_for_prompt(refs)` — bullet list for researcher prompts
- `create_read_web_site_refs_tool(context_dir)` → `read_web_site_refs(path="")` — Researcher tool

Used by `scripts/run_search.py` and the team enrichment workflow (Researcher instructions).

### `compiler_fs.py`

**Intent:** Safe file access when raw data lives in **more than one directory** or outside the default `context_dir/raw`.

- `create_compiler_file_tools` — `read_file`, `save_file`, `list_files` with paths under `wiki/` (writable) and `raw/` or `raw/<label>/` (read-only for compiler)
- `use_labelled_raw_paths` — Whether virtual `raw/<label>/...` paths are required

When only the default single `raw/` under context exists, the Compiler uses Agno `FileTools` instead.

## Data flow (simplified)

```
Researcher: Parallel + ingest_*  →  raw/*.md + .manifest.json
Compiler:   read raw, write wiki/, mark manifest compiled
Linter:     read wiki index/state, report gaps, update .state.json
Navigator:  SQL + files + read manifest/index for routing user work
```

## Adding a new tool

1. Implement a factory (e.g. `create_*_tools`) in a focused module, or extend an existing one.
2. Register it in the appropriate `build_*_tools` function in `builder.py`.
3. Document the tool docstring; agents rely on names and descriptions for when to call each tool.
