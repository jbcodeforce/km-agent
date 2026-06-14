"""Ingest tools — fetch URLs and save text to raw/ with frontmatter."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from agno.tools import tool

from kma.config import get_parallel_api_key, get_parallel_ingest_max_chars

def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-")


def _read_manifest(raw_dir: Path) -> list[dict]:
    manifest_path = raw_dir / ".manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())  # type: ignore[no-any-return]
    return []


def _write_manifest(raw_dir: Path, manifest: list[dict]) -> None:
    manifest_path = raw_dir / ".manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


def manifest_entry_compiled(raw_dir: Path, file_rel: str) -> bool:
    """Return whether ``file_rel`` is marked compiled in ``raw_dir/.manifest.json``."""
    for entry in _read_manifest(raw_dir):
        if entry.get("file") == file_rel:
            return bool(entry.get("compiled"))
    return False


def mark_manifest_compiled(raw_dir: Path, file_rel: str) -> bool:
    """Mark one manifest entry compiled. Returns True if the entry was found and updated."""
    manifest = _read_manifest(raw_dir)
    for entry in manifest:
        if entry.get("file") == file_rel:
            entry["compiled"] = True
            _write_manifest(raw_dir, manifest)
            return True
    return False


def _parse_frontmatter_lines(block: str) -> dict[str, str]:
    """Parse a YAML-ish frontmatter block into string keys (values stripped, quotes removed)."""
    meta: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        meta[key] = val
    return meta


def _normalize_ingested_iso(raw: str) -> str:
    """Match ingest manifest style ``YYYY-MM-DDTHH:MM:SSZ`` when possible."""
    raw = raw.strip()
    if not raw:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return f"{raw}T00:00:00Z"
    if "T" in raw and raw.endswith("Z"):
        return raw
    # best-effort: treat as date prefix
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return f"{m.group(1)}T00:00:00Z"
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compiled_bool(val: str) -> bool:
    return val.strip().lower() in ("true", "1", "yes")


def sync_manifest_from_raw_markdown(raw_dir: Path) -> str:
    """Rebuild ``raw_dir/.manifest.json`` from ``*.md`` files using each file's YAML frontmatter.

    Manifest rows match :func:`_do_ingest_text` / :func:`_do_ingest_url` (``file``, ``title``,
    ``source``, ``ingested``, ``compiled``). Overwrites any existing manifest.
    """
    raw_path = Path(raw_dir).resolve()
    if not raw_path.is_dir():
        return f"Not a directory: {raw_path}"

    rows: list[dict] = []
    for path in sorted(raw_path.glob("*.md")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        rest = text[3:].lstrip("\n")
        end = rest.find("\n---")
        if end == -1:
            continue
        fm_block = rest[:end]
        meta = _parse_frontmatter_lines(fm_block)
        title = meta.get("title", path.stem)
        source = meta.get("source", "")
        ingested = _normalize_ingested_iso(meta.get("ingested", ""))
        compiled = _compiled_bool(meta.get("compiled", "false"))
        rows.append(
            {
                "file": path.name,
                "title": title,
                "source": source,
                "ingested": ingested,
                "compiled": compiled,
            }
        )

    _write_manifest(raw_path, rows)
    return f"Synced {len(rows)} manifest entries under {raw_path}"


def _coerce_tags(tags: list[str] | str | None) -> list[str]:
    """Normalize tool ``tags`` — agents often pass a JSON array string."""
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    raw = tags.strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(t).strip() for t in parsed if str(t).strip()]
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in raw.split(",") if part.strip()]


def _build_frontmatter(title: str, source: str, tags: list[str], doc_type: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tag_str = ", ".join(tags) if tags else ""
    return (
        f"---\n"
        f'title: "{title}"\n'
        f"source: {source}\n"
        f"ingested: {now}\n"
        f"tags: [{tag_str}]\n"
        f"type: {doc_type}\n"
        f"compiled: false\n"
        f"---\n\n"
    )


def _do_ingest_url(raw_dir: Path, url: str, title: str, tags: list[str] | None = None, doc_type: str = "article") -> str:
    """Core ingest-URL logic (callable directly and via @tool wrapper)."""

    slug = _slugify(title)
    filename = f"{slug}.md"
    file_path = raw_dir / filename
    frontmatter = _build_frontmatter(title, url, tags or [], doc_type)

    # Try to fetch content via Parallel (bounded excerpts — keeps MLX context small)
    extracted = ""
    parallel_key = get_parallel_api_key()
    if parallel_key:
        try:
            from parallel import Parallel

            max_chars = get_parallel_ingest_max_chars()
            client = Parallel(api_key=parallel_key)
            result = client.beta.extract(
                urls=[url],
                excerpts={"max_chars_per_result": max_chars},
            )
            if result and result.results:
                r = result.results[0]
                if getattr(r, "excerpts", None):
                    extracted = "\n\n".join(r.excerpts)
                elif getattr(r, "full_content", None):
                    extracted = (r.full_content or "")[:max_chars]
        except Exception as e:
            extracted = f"*(Content extraction failed: {e}. Stub saved — fetch manually.)*"

    if extracted and not extracted.startswith("*(Content extraction failed"):
        file_path.write_text(frontmatter + extracted + "\n")
        status = f"Ingested with content: {filename} ({len(extracted)} chars)"
    else:
        stub = extracted or f"Source: {url}\n\n*(Content pending — configure PARALLEL_API_KEY or use ingest_text.)*"
        file_path.write_text(frontmatter + stub + "\n")
        status = f"Ingested stub: {filename}" + (" (extraction failed)" if extracted else "")

    # Update manifest
    manifest = _read_manifest(raw_dir)
    manifest.append(
        {
            "file": filename,
            "title": title,
            "source": url,
            "ingested": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "compiled": False,
        }
    )
    _write_manifest(raw_dir, manifest)

    return status


def _do_ingest_text(
    raw_dir: Path, title: str, content: str, source: str = "user", tags: list[str] | None = None, doc_type: str = "notes"
) -> str:
    """Core ingest-text logic (callable directly and via @tool wrapper)."""
    slug = _slugify(title)
    filename = f"{slug}.md"
    file_path = raw_dir / filename

    frontmatter = _build_frontmatter(title, source, tags or [], doc_type)
    file_path.write_text(frontmatter + content + "\n")

    # Update manifest
    manifest = _read_manifest(raw_dir)
    manifest.append(
        {
            "file": filename,
            "title": title,
            "source": source,
            "ingested": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "compiled": False,
        }
    )
    _write_manifest(raw_dir, manifest)

    return f"Ingested: {filename} ({len(content)} chars)"



def create_ingest_tools(raw_dir: Path) -> list:
    """Create ingest tools bound to the raw/ directory.

    Args:
        raw_dir: Path to raw/ (resolved from PAL_CONTEXT_DIR).

    Returns:
        List of tool functions.
    """

    @tool
    def ingest_url(
        url: str,
        title: str,
        tags: list[str] | str | None = None,
        doc_type: str = "article",
    ) -> str:
        """Ingest a URL into the knowledge base raw/ directory.

        Fetches page content via Parallel (if configured) and saves as a
        markdown file with YAML frontmatter in raw/. Falls back to
        a stub if Parallel is not configured or extraction fails.

        Args:
            url: The source URL.
            title: A descriptive title for the document.
            tags: Optional topic tags as a list or JSON array string (e.g. ["rag", "retrieval"]).
            doc_type: Document type: paper, article, repo, notes, transcript, image.

        Returns:
            Confirmation with the file path and content status.
        """
        return _do_ingest_url(raw_dir, url, title, _coerce_tags(tags), doc_type)

    @tool
    def ingest_text(
        title: str,
        content: str,
        source: str = "user",
        tags: list[str] | str | None = None,
        doc_type: str = "notes",
    ) -> str:
        """Ingest text content into the knowledge base raw/ directory.

        Saves text as a markdown file with YAML frontmatter in raw/.
        Use this for clipboard content, meeting notes, manually provided text,
        or content fetched from web research.

        Args:
            title: A descriptive title for the document.
            content: The markdown content to save.
            source: Where the content came from (URL, "user", "clipboard", etc.).
            tags: Optional topic tags as a list or JSON array string.
            doc_type: Document type: paper, article, repo, notes, transcript, image.

        Returns:
            Confirmation with the file path.
        """
        return _do_ingest_text(raw_dir, title, content, source, _coerce_tags(tags), doc_type)

    @tool
    def read_manifest() -> str:
        """Read the raw/ manifest to see all ingested documents and their compile status.

        Returns:
            JSON string of the manifest entries.
        """
        manifest = _read_manifest(raw_dir)
        if not manifest:
            return "No documents ingested yet. The raw/ directory is empty."
        return json.dumps(manifest, indent=2)

    @tool
    def update_manifest_compiled(filename: str) -> str:
        """Mark a raw document as compiled in the manifest.

        Call this after successfully compiling a raw document into wiki articles.

        Args:
            filename: The filename in raw/ to mark as compiled.

        Returns:
            Confirmation message.
        """
        if mark_manifest_compiled(raw_dir, filename):
            return f"Marked as compiled: {filename}"
        return f"Not found in manifest: {filename}"

    @tool
    def sync_raw_manifest_from_disk() -> str:
        """Rebuild .manifest.json from existing *.md files in raw/ using YAML frontmatter.

        Use when raw markdown was added or restored without going through ingest_url /
        ingest_text. Overwrites the current manifest.
        """
        return sync_manifest_from_raw_markdown(raw_dir)

    return [ingest_url, ingest_text, read_manifest, update_manifest_compiled, sync_raw_manifest_from_disk]


def _compiler_uses_labelled_manifest_ids(raw_roots: Sequence[tuple[str, Path]], context_dir: Path) -> bool:
    ctx = context_dir.resolve()
    default_raw = (ctx / "raw").resolve()
    if len(raw_roots) != 1:
        return True
    _, only = raw_roots[0]
    return only.resolve() != default_raw


def create_compiler_manifest_tools(
    context_dir: Path, raw_roots: Sequence[tuple[str, Path]]
) -> tuple[object, object]:
    """Merged ``read_manifest`` / ``update_manifest_compiled`` for one or more raw directories.

    Each raw root keeps its own ``.manifest.json``. When multiple roots or an external
    single raw path is used, entries include ``file_id`` as ``label:relpath`` for updates.
    """

    ctx = context_dir.resolve()
    roots: list[tuple[str, Path]] = [(str(lab), Path(root).resolve()) for lab, root in raw_roots]
    labelled = _compiler_uses_labelled_manifest_ids(roots, ctx)

    @tool
    def read_manifest() -> str:
        """Read merged manifests for all raw roots (see file_id when multiple roots)."""
        merged: list[dict] = []
        for label, raw_dir in roots:
            for entry in _read_manifest(raw_dir):
                row = dict(entry)
                rel = row.get("file", "")
                if labelled:
                    row["file_id"] = f"{label}:{rel}"
                else:
                    row["file_id"] = rel
                merged.append(row)
        if not merged:
            return "No documents ingested yet. The raw/ directory is empty."
        return json.dumps(merged, indent=2)

    @tool
    def update_manifest_compiled(filename: str) -> str:
        """Mark a raw document compiled. Use file_id from read_manifest (label:relpath if multi-root)."""
        key = filename.strip()
        if labelled and ":" in key:
            label, rel = key.split(":", 1)
            raw_home = next((r for lab, r in roots if lab == label), None)
            if raw_home is None:
                return f"Unknown raw root label: {label}"
            manifest = _read_manifest(raw_home)
            if mark_manifest_compiled(raw_home, rel):
                return f"Marked as compiled: {key}"
            return f"Not found in manifest: {key}"
        if len(roots) == 1:
            raw_home = roots[0][1]
            if mark_manifest_compiled(raw_home, key):
                return f"Marked as compiled: {key}"
            return f"Not found in manifest: {key}"
        # multi-root but caller passed bare file — ambiguous
        return (
            f"Not found in manifest: {key}. "
            "Use file_id label:relpath from read_manifest when multiple raw roots exist."
        )

    return read_manifest, update_manifest_compiled
