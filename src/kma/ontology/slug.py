"""Stable slug / IRI helpers for wiki entities."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from kma.ontology.namespaces import DATA


def slugify(text: str) -> str:
    """Convert display text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:120].strip("-") or "unknown"


def concept_slug_from_title(title: str) -> str:
    return slugify(title)


def concept_slug_from_path(wiki_path: str) -> str:
    """``wiki/concepts/apache-flink.md`` → ``apache-flink``."""
    name = PurePosixPath(wiki_path.replace("\\", "/")).stem
    return slugify(name)


def concept_iri(slug: str):
    return DATA[f"concept/{slug}"]


def summary_iri(slug: str):
    return DATA[f"summary/{slug}"]


def raw_iri(rel_path: str):
    rel = rel_path.replace("\\", "/").lstrip("/")
    return DATA[f"raw/{rel}"]


def code_iri(rel_path: str):
    rel = rel_path.replace("\\", "/").lstrip("/")
    return DATA[f"code/{rel}"]


def statement_iri(manifest_rel: str, group: str, name: str):
    safe = slugify(f"{manifest_rel}-{group}-{name}")
    return DATA[f"statement/{safe}"]
