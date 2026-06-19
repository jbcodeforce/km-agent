"""Parse YAML-ish frontmatter from wiki and raw markdown."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WikiFrontmatter:
    title: str = ""
    created: str = ""
    updated: str = ""
    sources: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_block, body) or (None, full_text)."""
    if not text.startswith("---"):
        return None, text
    rest = text[3:].lstrip("\n")
    end = rest.find("\n---")
    if end == -1:
        return None, text
    body = rest[end + 4 :].lstrip("\n")
    return rest[:end], body


def _parse_bracket_list(val: str) -> list[str]:
    val = val.strip()
    if not val:
        return []
    if val.startswith("["):
        try:
            parsed = json.loads(val.replace("'", '"'))
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            inner = val.strip("[]")
            return [p.strip().strip('"').strip("'") for p in inner.split(",") if p.strip()]
    return [val]


def parse_wiki_frontmatter(block: str) -> WikiFrontmatter:
    fm = WikiFrontmatter()
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        if key == "title":
            fm.title = val.strip('"').strip("'")
        elif key == "created":
            fm.created = val
        elif key == "updated":
            fm.updated = val
        elif key == "sources":
            fm.sources = _parse_bracket_list(val)
        elif key == "related":
            fm.related = _parse_bracket_list(val)
        elif key == "tags":
            fm.tags = _parse_bracket_list(val)
        elif key == "code":
            fm.code = _parse_bracket_list(val)
    return fm


def read_wiki_frontmatter(path: Path) -> tuple[WikiFrontmatter, str]:
    text = path.read_text(encoding="utf-8")
    block, body = split_frontmatter(text)
    if block is None:
        return WikiFrontmatter(title=path.stem), body
    fm = parse_wiki_frontmatter(block)
    if not fm.title:
        fm.title = path.stem
    return fm, body


_WIKILINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_body_wikilinks(body: str) -> list[tuple[str, str]]:
    """Return (label, target) pairs from markdown links in body."""
    out: list[tuple[str, str]] = []
    for label, target in _WIKILINK.findall(body):
        target = target.strip()
        if target.startswith("http://") or target.startswith("https://"):
            continue
        out.append((label.strip(), target))
    return out


_CODE_LINK = re.compile(
    r"(?:\]\(([^)]*code/[^)]+)\)|`([^`]*code/[^`]+)`|(?<![\w/])(code/[\w./-]+))",
    re.IGNORECASE,
)


def extract_code_path_refs(text: str) -> list[str]:
    """Find ``code/...`` path references in markdown."""
    found: set[str] = set()
    for m in _CODE_LINK.finditer(text):
        for g in m.groups():
            if g:
                found.add(g.replace("\\", "/").strip())
    return sorted(found)
