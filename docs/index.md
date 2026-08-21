# KM_Agent Introduction

???- Info "Version"
    - Created 06/2026
    - Update 08/2026
    

`km-agent` is a personal knowledge management agent to work on existing studies or new content discovered by the user. Studies or body of knowledge is kept inside markdown files that can be exposed as web site using mkdocs. Those notes are human created. While km-agent helps to create semantical searchable content using concepts, relationships and indexing like wiki. 

Users can also perform deep research to create raw materials. New content can be re-structured as wiki content via the different agents used in this solution.

* Agents supported are:

  ```sh
      ├── Navigator    — routes queries, reads wiki, handles SQL/files
      ├── Researcher   - web search, source gathering and write to context/raw/
      ├── Compiler     — reads raw/, writes wiki articles, maintains index
      ├── Linter       — health checks, finds gaps, suggests research
  ```

![](./images/agents_solution.drawio.png)


## Core Capabilities

### Knowledge Base Pipeline

There are two types of raw knowledge: the docs folder of a studies repository, like flink-studies, and new raw data discovered by the researcher agent.

```sh
├── docs
├── wiki
│   ├── raw
│   ├── entities
│   ├── concepts
│   index.md
│   SCHEMA.md
```

Raw data flows through a compilation pipeline into a structured wiki:

```sh
Ingest (Researcher)     →  context/raw/     →  context/.manifest.json tracks state
Compile (Compiler)      →  context/wiki/    →  concepts/, summaries/, index.md
Query (Navigator)       →  index-first and/or search_wiki →  pulls specific articles
File outputs (Navigator)→  wiki/outputs/    →  compounds back into wiki
Lint (Linter)           →  wiki/lint-report →  finds gaps, suggests research
```

- **Raw documents** have YAML frontmatter (title, source, date, tags, type, compiled status)
- **Wiki articles** have frontmatter (title, dates, sources, related concepts, tags)
- **Wiki index** lists all articles with 1-line summaries — fits in one LLM read (~5K tokens at 100 articles)
- **Manifest** tracks compile state per raw file — incremental, never rewrites the whole wiki

When articles come from docs of a studies repository the date of the file, and its content may change overtime after indexing so `compiler` may modify wiki concepts, index and summaries. 


### Execution Loop

Every interaction with the router agent follows five steps:

1. **Classify** — Determine intent from the user request.
2. **Recall** — Query SQL tables first (for retrieve/connect), then search knowledge, learnings, wiki index, and files.
3. **Read** — Pull from identified sources. Wiki-first for knowledge questions.
4. **Act** — Execute tool calls.
5. **Learn** — Save discoveries, retrieval strategies, and patterns.

### Context stores: Knowledge, Learnings, Wiki

Three systems serve different roles (see [architecture section](./architecture.md)):

- **`kma_knowledge`** — Metadata index (routing layer). File manifests (`File:`), table schemas (`Schema:`), source capabilities (`Source:`), cross-source discoveries (`Discovery:`), wiki articles (`Wiki:`), raw sources (`Raw:`). Not domain article bodies.
- **`kma_learnings`** — Operational memory. Retrieval strategies (`Retrieval:`), recurring patterns (`Pattern:`), explicit user corrections (`Correction:`). Corrections always take priority. Not domain content.
- **`context/wiki/`** — Compiled domain knowledge (markdown). Optional **`kma_wiki`** pgvector table for semantic chunk search via `search_wiki` after offline `scripts/index_wiki.py`.

**Bootstrap**: `context/load_context.py` populates `kma_knowledge` on first run by scanning the context directory, parsing YAML frontmatter for tags, and inserting `File:` metadata entries. This is the bootstrap step that makes Navigator's recall work — without it, the knowledge routing layer is empty. Supports `--recreate` (clear and reload) and `--dry-run` (preview). Also exposed via `/context/reload` endpoint and scheduled daily.

## Next

* [User Guide](./USER_GUIDE.md)
* [Develop of the solution guide](./DEVELOPER_PRACTICES.md)