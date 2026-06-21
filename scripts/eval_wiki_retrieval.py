#!/usr/bin/env python3
"""Compare wiki retrieval: index vs ontology graph vs optional semantic search_wiki.

Loads gold questions from tests/data/wiki_eval/questions.jsonl (or a custom JSONL),
rebuilds ontology when missing, and reports Recall@k, MRR, and Hit@1 per method.

Example:

  uv run python scripts/eval_wiki_retrieval.py --context ./tests/data
  uv run python scripts/eval_wiki_retrieval.py --context ./context --k 5 --semantic
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from kma.ontology.builder import rebuild_ontology  # noqa: E402
from kma.ontology.retrieval import (  # noqa: E402
    hit_at_1,
    load_graph_ttl,
    mrr,
    recall_at_k,
    search_wiki_index,
    wiki_paths_from_graph_query,
)

DEFAULT_QUESTIONS = REPO_ROOT / "tests" / "data" / "wiki_eval" / "questions.jsonl"


@dataclass
class EvalQuestion:
    id: str
    question: str
    gold_paths: list[str]
    gold_keywords: list[str]


@dataclass
class MethodScores:
    recall: float
    mrr: float
    hit1: float


def load_questions(path: Path) -> list[EvalQuestion]:
    questions: list[EvalQuestion] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        questions.append(
            EvalQuestion(
                id=row["id"],
                question=row["question"],
                gold_paths=list(row.get("gold_paths", [])),
                gold_keywords=list(row.get("gold_keywords", [])),
            )
        )
    return questions


def ensure_ontology(context_dir: Path, studies_root: Path | None) -> Path:
    ontology_dir = context_dir / "ontology"
    graph_ttl = ontology_dir / "graph.ttl"
    if not graph_ttl.exists():
        print(f"building ontology under {ontology_dir} ...")
        rebuild_ontology(context_dir, studies_root=studies_root)
    return graph_ttl


def semantic_paths(context_dir: Path, query: str, max_results: int) -> list[str]:
    from kma.db import create_knowledge

    wiki_dir = context_dir / "wiki"
    knowledge = create_knowledge("kma Wiki", "kma_wiki_eval")
    docs = knowledge.search(query, max_results=max_results)
    paths: list[str] = []
    for doc in docs:
        meta = doc.meta_data or {}
        path = meta.get("wiki_path")
        if path:
            paths.append(str(path))
        elif meta.get("name", "").startswith("Wiki: "):
            paths.append(meta["name"][6:].strip())
        elif doc.name and doc.name.startswith("Wiki: "):
            rel = doc.name[6:].strip()
            if (wiki_dir / rel).exists():
                paths.append(rel)
    return paths


def evaluate_method(
    questions: list[EvalQuestion],
    retrieve,
    k: int,
) -> MethodScores:
    recalls: list[float] = []
    mrrs: list[float] = []
    hits: list[float] = []
    for q in questions:
        paths = retrieve(q)
        recalls.append(recall_at_k(paths, q.gold_paths, k))
        mrrs.append(mrr(paths, q.gold_paths))
        hits.append(hit_at_1(paths, q.gold_paths))
    n = len(questions) or 1
    return MethodScores(
        recall=sum(recalls) / n,
        mrr=sum(mrrs) / n,
        hit1=sum(hits) / n,
    )


def print_report(
    questions: list[EvalQuestion],
    k: int,
    scores: dict[str, MethodScores],
) -> None:
    print(f"questions: {len(questions)} | Recall@{k}")
    print("-" * 56)
    header = f"{'method':<18} {'recall@k':>10} {'mrr':>10} {'hit@1':>10}"
    print(header)
    print("-" * 56)
    for name, s in scores.items():
        print(f"{name:<18} {s.recall:>10.3f} {s.mrr:>10.3f} {s.hit1:>10.3f}")
    print("-" * 56)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate wiki retrieval methods on gold questions.")
    parser.add_argument(
        "--context",
        type=Path,
        default=REPO_ROOT / "tests" / "data",
        help="Context dir containing wiki/ (default: tests/data)",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS,
        help="JSONL gold questions file",
    )
    parser.add_argument("--k", type=int, default=5, help="Top-k for Recall@k")
    parser.add_argument(
        "--studies-root",
        type=Path,
        default=None,
        help="Optional studies repo root for code-linked ontology triples",
    )
    parser.add_argument(
        "--semantic",
        action="store_true",
        help="Include search_wiki via kma_wiki_eval table (requires Postgres + index)",
    )
    parser.add_argument(
        "--expand-neighbors",
        type=int,
        default=1,
        help="Ontology relatedTo expansion hops",
    )
    args = parser.parse_args()

    context_dir = args.context.resolve()
    if not (context_dir / "wiki").is_dir():
        print(f"error: wiki dir missing: {context_dir / 'wiki'}", file=sys.stderr)
        return 1

    questions_path = args.questions.resolve()
    if not questions_path.is_file():
        print(f"error: questions file missing: {questions_path}", file=sys.stderr)
        return 1

    questions = load_questions(questions_path)
    graph_ttl = ensure_ontology(context_dir, args.studies_root)
    graph = load_graph_ttl(graph_ttl)
    index_text = (context_dir / "wiki" / "index.md").read_text(encoding="utf-8")

    scores: dict[str, MethodScores] = {}

    scores["index"] = evaluate_method(
        questions,
        lambda q: search_wiki_index(index_text, q.question, max_results=args.k),
        args.k,
    )
    scores["ontology"] = evaluate_method(
        questions,
        lambda q: wiki_paths_from_graph_query(
            graph,
            q.question,
            expand_neighbors=args.expand_neighbors,
            max_results=args.k,
        ),
        args.k,
    )

    if args.semantic:
        try:
            scores["search_wiki"] = evaluate_method(
                questions,
                lambda q: semantic_paths(context_dir, q.question, max_results=args.k),
                args.k,
            )
        except Exception as exc:
            print(f"warning: semantic eval skipped ({exc})", file=sys.stderr)

    print_report(questions, args.k, scores)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
