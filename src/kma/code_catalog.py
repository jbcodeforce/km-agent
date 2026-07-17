"""Catalog studies ``code/`` (or ``src/``) into wiki concept pages with intent summaries."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from kma.ontology.frontmatter import read_wiki_frontmatter
from kma.ontology.slug import slugify

SKIP_DIR_NAMES = frozenset(
    {
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "target",
        ".terraform",
        ".git",
        ".pytest_cache",
        "images",
        "logs",
        "tmp",
        "data",
        "dist",
        "build",
        ".mvn",
    }
)

README_NAMES = ("README.md", "readme.md", "README.MD")
NOTABLE_GLOBS = ("*.sql", "*.py", "*.java",  "deploy_manifest.json", "Makefile", "makefile")
README_CHAR_CAP = 4000
INDEX_SECTION = "## Code catalogs"
PACK_HASH_MARKER = "<!-- kma-pack-hash:"

SummarizeFn = Callable[["LabPack"], "IntentSummary"]


@dataclass(frozen=True)
class LabPack:
    """Deterministic context for one lab / demo directory."""

    rel_path: str
    name: str
    readme_excerpt: str
    notable_files: tuple[str, ...]

    def content_hash(self) -> str:
        payload = json.dumps(
            {
                "rel": self.rel_path,
                "readme": self.readme_excerpt,
                "files": list(self.notable_files),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class IntentSummary:
    intent: str
    tags: tuple[str, ...] = ()


@dataclass
class CatalogStats:
    categories: int = 0
    labs: int = 0
    written: int = 0
    skipped_unchanged: int = 0
    llm_calls: int = 0


@dataclass
class CategoryCatalog:
    name: str
    rel_path: str
    intro: str
    labs: list[tuple[LabPack, IntentSummary]] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return f"code-{slugify(self.name)}"

    @property
    def title(self) -> str:
        display = self.name.replace("-", " ").replace("_", " ").strip()
        display = " ".join(p.capitalize() if p.islower() else p for p in display.split())
        return f"Code: {display}"


def discover_code_root(studies_root: Path, *, code_subdir: str | None = None) -> Path:
    """Return ``code/`` or ``src/`` under studies_root (or explicit subdirectory)."""
    root = studies_root.resolve()
    if code_subdir:
        candidate = root / code_subdir
        if not candidate.is_dir():
            raise FileNotFoundError(f"code subdirectory not found: {candidate}")
        return candidate
    for name in ("code", "src"):
        candidate = root / name
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"no code/ or src/ under {root}")


def _should_skip_dir(name: str) -> bool:
    if name.startswith("."):
        return True
    if name in SKIP_DIR_NAMES:
        return True
    if name.endswith("_old"):
        return True
    return False


def iter_categories(code_root: Path) -> list[Path]:
    """Top-level category directories under the code root."""
    if not code_root.is_dir():
        return []
    cats = [
        p
        for p in sorted(code_root.iterdir())
        if p.is_dir() and not _should_skip_dir(p.name)
    ]
    return cats


def iter_labs(category_dir: Path) -> list[Path]:
    """Immediate meaningful subdirectories treated as labs/demos."""
    if not category_dir.is_dir():
        return []
    return [
        p
        for p in sorted(category_dir.iterdir())
        if p.is_dir() and not _should_skip_dir(p.name)
    ]


def _find_readme(directory: Path) -> Path | None:
    for name in README_NAMES:
        path = directory / name
        if path.is_file():
            return path
    return None


def _first_paragraph(markdown: str) -> str:
    """Return first non-heading, non-empty prose paragraph."""
    lines = markdown.replace("\r\n", "\n").split("\n")
    buf: list[str] = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not started:
            if not stripped or stripped.startswith("#") or stripped.startswith("|"):
                continue
            if stripped.startswith("```"):
                continue
            if stripped.startswith("---"):
                continue
            started = True
            buf.append(stripped)
            continue
        if not stripped:
            break
        if stripped.startswith("#") or stripped.startswith("|"):
            break
        buf.append(stripped)
    return " ".join(buf).strip()


def extract_blurb_from_readme(readme_text: str, lab_name: str | None = None) -> str:
    """Prefer a matching ``## lab`` section; else first paragraph."""
    if lab_name:
        pattern = re.compile(
            rf"^##\s+{re.escape(lab_name)}\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(readme_text)
        if match:
            rest = readme_text[match.end() :]
            next_h2 = re.search(r"^##\s+", rest, re.MULTILINE)
            section = rest[: next_h2.start()] if next_h2 else rest
            para = _first_paragraph(section)
            if para:
                return para
    return _first_paragraph(readme_text)


def build_lab_pack(lab_dir: Path, studies_root: Path) -> LabPack:
    """Build capped README + notable-file pack for LLM / fallback summarization."""
    studies_root = studies_root.resolve()
    lab_dir = lab_dir.resolve()
    rel = lab_dir.relative_to(studies_root).as_posix()
    readme = _find_readme(lab_dir)
    readme_text = ""
    if readme is not None:
        raw = readme.read_text(encoding="utf-8", errors="replace")
        readme_text = raw[:README_CHAR_CAP]
    parent_readme = _find_readme(lab_dir.parent)
    if not readme_text and parent_readme is not None:
        parent_text = parent_readme.read_text(encoding="utf-8", errors="replace")
        blurb = extract_blurb_from_readme(parent_text, lab_dir.name)
        readme_text = blurb[:README_CHAR_CAP]

    notable: list[str] = []
    for pattern in NOTABLE_GLOBS:
        for path in sorted(lab_dir.rglob(pattern)):
            if not path.is_file():
                continue
            parts = set(path.relative_to(lab_dir).parts)
            if parts & SKIP_DIR_NAMES:
                continue
            if any(p.startswith(".") for p in path.relative_to(lab_dir).parts):
                continue
            notable.append(path.relative_to(studies_root).as_posix())
            if len(notable) >= 24:
                break
        if len(notable) >= 24:
            break

    return LabPack(
        rel_path=rel,
        name=lab_dir.name,
        readme_excerpt=readme_text.strip(),
        notable_files=tuple(notable),
    )


def fallback_intent(pack: LabPack) -> IntentSummary:
    """Deterministic blurb when LLM is disabled."""
    if pack.readme_excerpt:
        intent = extract_blurb_from_readme(pack.readme_excerpt) or pack.readme_excerpt.split("\n")[0]
        intent = intent.strip()
        if len(intent) > 400:
            intent = intent[:397].rstrip() + "..."
    else:
        human = pack.name.replace("-", " ").replace("_", " ")
        intent = f"Studies lab `{pack.name}` ({human}) at `{pack.rel_path}`."
    return IntentSummary(intent=intent, tags=())


def build_intent_prompt(pack: LabPack) -> str:
    files = "\n".join(f"- {f}" for f in pack.notable_files[:16]) or "- (none listed)"
    readme = pack.readme_excerpt or "(no README excerpt)"
    return (
        "You write short wiki blurbs for a knowledge-management agent so chat search "
        "can find the right code demo.\n\n"
        f"Lab path: `{pack.rel_path}`\n"
        f"Lab name: {pack.name}\n\n"
        "README excerpt:\n"
        f"{readme}\n\n"
        "Notable files:\n"
        f"{files}\n\n"
        "Respond with ONLY valid JSON (no markdown fences):\n"
        '{"intent": "2-4 sentences: what problem this lab teaches, key concepts, '
        'when to open it", "tags": ["keyword1", "keyword2"]}\n'
        "Keep intent under 80 words. Do not paste large code. tags: 3-6 lowercase tokens."
    )


def summarize_lab_intent_with_agent(pack: LabPack) -> IntentSummary:
    """Call configured KMA LLM via a tool-free Agno Agent."""
    from agno.agent import Agent

    from kma.llm_factory import build_default_llm_model

    agent = Agent(
        name="code-catalog-intent",
        model=build_default_llm_model(),
        instructions=[
            "Return only the requested JSON object. No tooling. No preamble.",
        ],
        markdown=False,
    )
    out = agent.run(build_intent_prompt(pack))
    content = (out.content or "").strip() if out is not None else ""
    return _parse_intent_response(content, pack)


def _parse_intent_response(content: str, pack: LabPack) -> IntentSummary:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find a JSON object substring
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return IntentSummary(intent=text[:500] or fallback_intent(pack).intent)
        else:
            return IntentSummary(intent=text[:500] or fallback_intent(pack).intent)
    intent = str(data.get("intent") or "").strip()
    tags_raw = data.get("tags") or []
    tags: list[str] = []
    if isinstance(tags_raw, list):
        tags = [str(t).strip().lower() for t in tags_raw if str(t).strip()]
    if not intent:
        return fallback_intent(pack)
    return IntentSummary(intent=intent, tags=tuple(tags[:8]))


def _existing_pack_hash(page_path: Path) -> str | None:
    if not page_path.is_file():
        return None
    text = page_path.read_text(encoding="utf-8")
    match = re.search(rf"{re.escape(PACK_HASH_MARKER)}\s*([0-9a-f]+)\s*-->", text)
    return match.group(1) if match else None


def _category_pack_hash(packs: list[LabPack]) -> str:
    joined = "|".join(f"{p.rel_path}:{p.content_hash()}" for p in packs)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _format_bracket_list(items: list[str]) -> str:
    if not items:
        return "[]"
    escaped = [json.dumps(i) for i in items]
    return "[" + ", ".join(escaped) + "]"


def render_category_page(
    catalog: CategoryCatalog,
    *,
    created: str | None = None,
    pack_hash: str,
) -> str:
    today = date.today().isoformat()
    code_paths = [pack.rel_path for pack, _ in catalog.labs]
    tags = ["code", slugify(catalog.name), "studies"]
    for _, summary in catalog.labs:
        for t in summary.tags:
            if t and t not in tags:
                tags.append(t)
        if len(tags) >= 12:
            break

    lines = [
        "---",
        f'title: "{catalog.title}"',
        f"created: {created or today}",
        f"updated: {today}",
        "sources: []",
        "related: []",
        f"tags: {_format_bracket_list(tags)}",
        f"code: {_format_bracket_list(code_paths)}",
        "---",
        "",
        f"# {catalog.title}",
        "",
        f"{PACK_HASH_MARKER} {pack_hash} -->",
        "",
    ]
    if catalog.intro:
        lines.extend([catalog.intro.strip(), ""])

    lines.append("## Labs")
    lines.append("")
    for pack, summary in catalog.labs:
        notable = ", ".join(Path(f).name for f in pack.notable_files[:6]) or "—"
        lines.extend(
            [
                f"### {pack.name}",
                summary.intent.strip(),
                f"- Path: `{pack.rel_path}`",
                f"- Notable: {notable}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def merge_code_catalogs_into_index(index_path: Path, entries: list[tuple[str, str, str]]) -> None:
    """Replace or append the ``## Code catalogs`` section.

    ``entries``: (title, wiki_rel_link, one_line_summary)
    """
    section_body_lines = ["## Code catalogs", ""]
    if entries:
        for title, link, summary in entries:
            section_body_lines.append(f"- [{title}]({link}) — {summary}")
        section_body_lines.append("")
    else:
        section_body_lines.append("_No code catalogs yet._")
        section_body_lines.append("")
    new_section = "\n".join(section_body_lines)

    if not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("# Wiki Index\n\n" + new_section, encoding="utf-8")
        return

    text = index_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"## Code catalogs\n.*?(?=\n## |\Z)",
        re.DOTALL,
    )
    if pattern.search(text):
        updated = pattern.sub(new_section.rstrip() + "\n\n", text)
    else:
        updated = text.rstrip() + "\n\n" + new_section
    index_path.write_text(updated, encoding="utf-8")


def write_code_catalog(
    context_dir: Path,
    studies_root: Path,
    *,
    code_subdir: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    use_llm: bool = True,
    limit: int | None = None,
    summarize: SummarizeFn | None = None,
) -> CatalogStats:
    """Scan studies code tree and write ``wiki/concepts/code-*.md`` pages."""
    ctx = context_dir.resolve()
    studies = studies_root.resolve()
    code_root = discover_code_root(studies, code_subdir=code_subdir)
    stats = CatalogStats()

    summarize_fn: SummarizeFn
    if summarize is not None:
        summarize_fn = summarize
    elif use_llm:
        summarize_fn = summarize_lab_intent_with_agent
    else:
        summarize_fn = fallback_intent

    wiki = ctx / "wiki"
    concepts = wiki / "concepts"
    if not dry_run:
        concepts.mkdir(parents=True, exist_ok=True)

    index_entries: list[tuple[str, str, str]] = []
    lab_budget = limit

    for category_dir in iter_categories(code_root):
        stats.categories += 1
        lab_dirs = iter_labs(category_dir)
        if lab_budget is not None:
            lab_dirs = lab_dirs[:lab_budget]
            lab_budget = max(0, lab_budget - len(lab_dirs))

        packs = [build_lab_pack(lab, studies) for lab in lab_dirs]
        # If category has no lab subdirs but has notable content itself, treat as one lab
        if not packs:
            packs = [build_lab_pack(category_dir, studies)]

        stats.labs += len(packs)
        page_path = concepts / f"code-{slugify(category_dir.name)}.md"
        cat_hash = _category_pack_hash(packs)

        if not force and _existing_pack_hash(page_path) == cat_hash:
            stats.skipped_unchanged += 1
            # Still list in index from existing page
            if page_path.is_file():
                fm, _ = read_wiki_frontmatter(page_path)
                title = fm.title or f"Code: {category_dir.name}"
                one_line = extract_blurb_from_readme(
                    page_path.read_text(encoding="utf-8")
                ) or title
                if len(one_line) > 160:
                    one_line = one_line[:157] + "..."
                index_entries.append(
                    (title, f"wiki/concepts/{page_path.name}", one_line)
                )
            if lab_budget == 0:
                break
            continue

        created: str | None = None
        if page_path.is_file():
            fm, _ = read_wiki_frontmatter(page_path)
            created = fm.created or None

        cat_readme = _find_readme(category_dir)
        intro = ""
        if cat_readme is not None:
            intro = extract_blurb_from_readme(
                cat_readme.read_text(encoding="utf-8", errors="replace")[:README_CHAR_CAP]
            )

        lab_rows: list[tuple[LabPack, IntentSummary]] = []
        for pack in packs:
            if dry_run:
                summary = fallback_intent(pack)
            else:
                summary = summarize_fn(pack)
                if use_llm:
                    stats.llm_calls += 1
            lab_rows.append((pack, summary))

        catalog = CategoryCatalog(
            name=category_dir.name,
            rel_path=category_dir.relative_to(studies).as_posix(),
            intro=intro,
            labs=lab_rows,
        )
        body = render_category_page(catalog, created=created, pack_hash=cat_hash)
        one_line = intro or (lab_rows[0][1].intent if lab_rows else catalog.title)
        if len(one_line) > 160:
            one_line = one_line[:157] + "..."
        index_entries.append(
            (catalog.title, f"wiki/concepts/{catalog.slug}.md", one_line)
        )

        if dry_run:
            print(f"would write: wiki/concepts/{catalog.slug}.md ({len(packs)} lab(s))")
            for pack, summary in lab_rows:
                print(f"  - {pack.rel_path}: {summary.intent[:80]}...")
        else:
            page_path.write_text(body, encoding="utf-8")
            stats.written += 1
            print(f"wrote: wiki/concepts/{catalog.slug}.md ({len(packs)} lab(s))")

        if lab_budget == 0:
            break

    if not dry_run:
        merge_code_catalogs_into_index(wiki / "index.md", index_entries)
        print(f"updated: wiki/index.md ({len(index_entries)} code catalog entries)")
    else:
        print(f"would update wiki/index.md with {len(index_entries)} entries")

    return stats
