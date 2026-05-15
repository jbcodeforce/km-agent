# Knowledge Management Agent (km-agent)

**km-agent** is an agentic workspace that turns your study materials and newly discovered sources into a **structured, queryable knowledge base** you can talk to through chat. It is inspired by the [Karpathy LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) and Agno [Pal](https://github.com/agno-agi/pal) project and built on [Agno](https://github.com/agno-agi/agno) **AgentOS**, PostgreSQL with **pgvector**, and an optional **Vue** chat UI. 

---

## Why this exists

Technical notes, knowledge repos (for example my [flink-studies](https://github.com/jbcodeforce/flink-studies)), and ad-hoc web findings usually live in different places: Git folders, bookmarks, Slack threads, and SQL databases. km-agent gives you a **single pipeline and a coordinated team of agents** so that material is **ingested**, **compiled into a wiki**, and **answered against** with context from files, SQL, and vector search—without you manually maintaining a separate “second brain” by hand.

---

## What you get

The high level architectrure view looks like:

![](./docs/images/agents_solution.drawio.png)


| Outcome | What it means for you |
|--------|------------------------|
| **A living wiki** | Raw markdown under `context/raw/` is incrementally compiled into `context/wiki/` (concepts, summaries, index)—not a one-off export. |
| **One chat surface** | A **Navigator**-style agent routes questions across wiki index, articles, your `kma` SQL schema, files under `context/`, and Agno **Knowledge** / learnings stores. |
| **Research → raw → wiki** | With **Parallel** configured (`PARALLEL_API_KEY`), a **Researcher** agent can gather web sources into `raw/`; the **Compiler** turns uncompiled sources into wiki updates. |
| **Direct compiler access** | The **Compiler** is also exposed on AgentOS for **HTTP runs** (e.g. automation or `scripts/compile_docs_folder.py`) in addition to team coordination. |
| **Persistent memory** | Sessions, hybrid vector + keyword search over **knowledge** tables, and **agentic learnings** live in **Postgres**—conversations and retrieval improve over time. |
| **Local-first option** | Run **Ollama** on the host for chat and embeddings when you want models and data under your control; **OpenAI** / **Anthropic** are supported when you prefer cloud LLMs. |
| **Web UI for development** | `src/frontend` is a small **Vue + Vite** app that proxies to AgentOS so you can exercise agents locally without writing API clients first. |

You keep ownership of the **`context/`** tree and your database; the repo is the glue between **AgentOS**, **agents (`kma`)**, and your environment.

---

## How it fits together (short)

1. **AgentOS** (`src/app/main.py`) serves the FastAPI app and wires **teams**, **agents**, **Postgres**, and **Knowledge** bases.  
2. **`kma` team** (`src/kma/team.py`) coordinates **Navigator**, **Compiler**, and optionally **Researcher** members.  
3. **Tools** under `src/kma/tools/` connect SQL, filesystem, wiki/manifest operations, and ingestion to that team.

For full architecture, capabilities (intents, memory tiers, context layout), and roadmap-level detail, see **[`docs/SPEC.md`](./docs/SPEC.md)**.

---

## Specifications

- [`SPEC.md`](./docs/SPEC.md)— product and system specification (agents, pipeline, knowledge model, context directory).  
- [`DEVELOPER_PRACTICES.md`](./docs/DEVELOPER_PRACTICES.md) — Postgres and Docker, Ollama, frontend layout and env, tests, integration gates.
- [`USER_GUIDE.md`](./docs/USER_GUIDE.md) - User use cases and how tos. 
---

## Getting started

1. **Clone** the repository and copy environment defaults:  
   `cp example.env .env` then edit **database**, **LLM**, and optional **Parallel** / **OpenAI** / **Anthropic** variables to match your machine.

---

## License and attribution

This repository is licensed under **[Apache License 2.0](./LICENSE)**. km-agent builds on **Agno** and patterns from **Pal**; see also dependency metadata from `uv` / `pyproject.toml` for third-party terms.
