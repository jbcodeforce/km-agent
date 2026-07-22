"""Ingest tools — fetch URLs and save text to raw/ with frontmatter."""

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Sequence

import httpx
from agno.tools import tool

from kma.config import get_ingest_max_chars


class _HTMLTextExtractor(HTMLParser):
    """Strip tags/scripts/styles and collect visible text."""

    _SKIP = frozenset({"script", "style", "noscript", "svg", "template"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag.lower() in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self._parts)).strip()


def _fetch_url_text(url: str, max_chars: int) -> str:
    """Fetch a URL and return plain text (bounded). Raises on hard failures."""
    headers = {"User-Agent": "km-agent/0.1 (+local research ingest)"}
    with httpx.Client(follow_redirects=True, timeout=20.0, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").lower()
        body = resp.text
    if "html" in content_type or body.lstrip().lower().startswith("<!"):
        parser = _HTMLTextExtractor()
        parser.feed(body)
        text = parser.text()
    else:
        text = body.strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n*(truncated)*"
    return text

def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-")


MANIFEST_FILENAME = ".manifest.json"
INGESTED_LABEL = "ingested"


def context_manifest_path(context_dir: Path) -> Path:
    """Return ``<context>/.manifest.json`` — the single shared manifest for all raw roots."""
    return Path(context_dir).resolve() / MANIFEST_FILENAME


def make_file_id(label: str, file_rel: str) -> str:
    """Build a stable ``label:relpath`` id (e.g. ``studies:sql/joins.md``)."""
    rel = str(file_rel).replace("\\", "/").lstrip("/")
    return f"{label}:{rel}"


def split_file_id(file_id: str) -> tuple[str, str]:
    """Split ``label:relpath`` into ``(label, rel)``. Bare paths use the ingested label."""
    key = (file_id or "").strip()
    if ":" in key:
        label, rel = key.split(":", 1)
        if label and rel:
            return label, rel
    return INGESTED_LABEL, key


def _entry_file_id(entry: dict) -> str:
    """Resolve ``file_id`` from an entry, including legacy rows that only have ``file``."""
    fid = entry.get("file_id")
    if fid:
        return str(fid)
    rel = entry.get("file")
    if rel:
        return make_file_id(INGESTED_LABEL, str(rel))
    return ""


def _find_manifest_entry(manifest: list[dict], file_id: str) -> dict | None:
    """Find an entry by ``file_id``, with legacy ``file``-only fallback."""
    key = file_id.strip()
    label, rel = split_file_id(key)
    for entry in manifest:
        if _entry_file_id(entry) == key:
            return entry
        if _entry_file_id(entry) == make_file_id(label, rel):
            return entry
        # Legacy bare filename under ingested
        if entry.get("file") == rel and not entry.get("file_id"):
            return entry
        if entry.get("file") == key and not entry.get("file_id"):
            return entry
    return None


def _read_manifest(context_dir: Path) -> list[dict]:
    """Load ``context/.manifest.json`` (empty list if missing)."""
    manifest_path = context_manifest_path(context_dir)
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {manifest_path}: {e}") from e
    if not isinstance(data, list):
        raise ValueError(f"Manifest must be a JSON array: {manifest_path}")
    return data  # type: ignore[no-any-return]


def _write_manifest(context_dir: Path, manifest: list[dict]) -> None:
    """Write ``context/.manifest.json``."""
    context = Path(context_dir).resolve()
    context.mkdir(parents=True, exist_ok=True)
    manifest_path = context_manifest_path(context)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def ensure_manifest_exists(context_dir: Path) -> Path:
    """Create an empty ``context/.manifest.json`` if missing. Returns the path."""
    path = context_manifest_path(context_dir)
    if not path.exists():
        _write_manifest(context_dir, [])
    return path


def manifest_entry_compiled(context_dir: Path, file_id: str) -> bool:
    """Return whether ``file_id`` is marked compiled in ``context/.manifest.json``."""
    entry = _find_manifest_entry(_read_manifest(context_dir), file_id)
    return bool(entry and entry.get("compiled"))


def mark_manifest_compiled(context_dir: Path, file_id: str) -> bool:
    """Mark one manifest entry compiled. Returns True if the entry was found and updated."""
    return set_manifest_compiled(context_dir, file_id, True)


def set_manifest_compiled(context_dir: Path, file_id: str, compiled: bool) -> bool:
    """Set ``compiled`` on one manifest entry. Returns True if the entry was found and updated."""
    manifest = _read_manifest(context_dir)
    entry = _find_manifest_entry(manifest, file_id)
    if entry is None:
        return False
    entry["compiled"] = compiled
    # Normalize id on write
    if not entry.get("file_id"):
        entry["file_id"] = make_file_id(*split_file_id(file_id))
    _write_manifest(context_dir, manifest)
    return True


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of ``path`` file bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_entry_sha256(context_dir: Path, file_id: str) -> str | None:
    """Return stored ``sha256`` for ``file_id``, or None if missing."""
    entry = _find_manifest_entry(_read_manifest(context_dir), file_id)
    if entry is None:
        return None
    value = entry.get("sha256")
    return str(value) if value else None


def manifest_content_unchanged(context_dir: Path, file_id: str, path: Path) -> bool:
    """True only when a stored sha256 exists and matches the current file bytes."""
    stored = manifest_entry_sha256(context_dir, file_id)
    if not stored:
        return False
    return stored == sha256_file(path)


def set_manifest_sha256(context_dir: Path, file_id: str, digest: str) -> bool:
    """Set ``sha256`` on the matching entry, or append a minimal row if missing."""
    manifest = _read_manifest(context_dir)
    entry = _find_manifest_entry(manifest, file_id)
    label, rel = split_file_id(file_id)
    canonical = make_file_id(label, rel)
    if entry is not None:
        entry["sha256"] = digest
        entry["file_id"] = canonical
        entry.setdefault("file", rel)
        _write_manifest(context_dir, manifest)
        return True
    manifest.append(
        {
            "file_id": canonical,
            "file": rel,
            "compiled": False,
            "sha256": digest,
        }
    )
    _write_manifest(context_dir, manifest)
    return True


def list_uncompiled_file_ids(context_dir: Path) -> list[str]:
    """Return manifest ``file_id`` values where ``compiled`` is false."""
    out: list[str] = []
    for entry in _read_manifest(context_dir):
        fid = _entry_file_id(entry)
        if not fid:
            continue
        if not entry.get("compiled"):
            out.append(fid)
    return out


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


def sync_manifest_from_raw_markdown(
    context_dir: Path,
    *,
    label: str = INGESTED_LABEL,
    raw_dir: Path | None = None,
) -> str:
    """Rebuild ``ingested:*`` (or ``label:*``) rows in ``context/.manifest.json`` from raw markdown.

    Other labels' entries are preserved. Rows match :func:`_do_ingest_text` shape
    (``file_id``, ``file``, ``title``, ``source``, ``ingested``, ``compiled``).
    """
    context = Path(context_dir).resolve()
    raw_path = Path(raw_dir).resolve() if raw_dir is not None else (context / "raw")
    if not raw_path.is_dir():
        return f"Not a directory: {raw_path}"

    prefix = f"{label}:"
    kept = [e for e in _read_manifest(context) if not _entry_file_id(e).startswith(prefix)]
    # Drop legacy bare-file rows when refreshing ingested
    if label == INGESTED_LABEL:
        kept = [e for e in kept if e.get("file_id") or not e.get("file")]

    rows: list[dict] = list(kept)
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
                "file_id": make_file_id(label, path.name),
                "file": path.name,
                "title": title,
                "source": source,
                "ingested": ingested,
                "compiled": compiled,
            }
        )

    _write_manifest(context, rows)
    return f"Synced {len(rows) - len(kept)} {label} manifest entries under {context_manifest_path(context)}"


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


DEFAULT_EXCLUDE_DIR_NAMES = frozenset(
    {".git", "node_modules", ".venv", ".venvs", "__pycache__", ".tox", "dist", "build"}
)


def has_yaml_frontmatter(text: str) -> bool:
    """Return True when ``text`` begins with a closed YAML ``---`` block."""
    if not text.startswith("---\n"):
        return False
    close = text.find("\n---\n", 4)
    return close != -1


def has_km_raw_frontmatter(text: str) -> bool:
    """Return True when ``text`` has km-agent raw frontmatter (title, source, compiled)."""
    if not has_yaml_frontmatter(text):
        return False
    close = text.find("\n---\n", 4)
    block = text[:close] if close != -1 else ""
    return "compiled:" in block and "title:" in block and "source:" in block


def strip_yaml_frontmatter(text: str) -> str:
    """Return markdown body after removing a leading YAML frontmatter block."""
    if not has_yaml_frontmatter(text):
        return text
    end = text.find("\n---\n", 4)
    return text[end + len("\n---\n") :].lstrip("\n")


def first_h1_title(body: str) -> str | None:
    """Return the first ``# heading`` text in ``body``, if any."""
    for line in body.splitlines():
        m = re.match(r"^#\s+(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return None


def title_from_markdown(body: str, *, fallback_stem: str) -> str:
    """Resolve a document title from the first H1 or a filename stem."""
    return first_h1_title(body) or fallback_stem.replace("-", " ").replace("_", " ").title()


def should_skip_markdown_path(path: Path, root: Path, exclude_dir_names: frozenset[str] = DEFAULT_EXCLUDE_DIR_NAMES) -> bool:
    """Skip hidden files and paths under excluded directory names."""
    if path.name.startswith("."):
        return True
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(part in exclude_dir_names for part in rel.parts)


def iter_markdown_files(
    root: Path,
    *,
    exclude_dir_names: frozenset[str] = DEFAULT_EXCLUDE_DIR_NAMES,
) -> list[Path]:
    """Return sorted ``*.md`` files under ``root``, skipping excluded directories."""
    docs_root = root.resolve()
    out: list[Path] = []
    for path in sorted(docs_root.rglob("*.md")):
        if not path.is_file():
            continue
        if should_skip_markdown_path(path, docs_root, exclude_dir_names):
            continue
        out.append(path)
    return out


def append_manifest_entry(
    context_dir: Path,
    file_id: str,
    title: str,
    source: str,
    *,
    reset_compiled: bool = False,
) -> None:
    """Insert or update one row in ``context/.manifest.json`` keyed by ``file_id``."""
    manifest = _read_manifest(context_dir)
    ingested = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    label, rel = split_file_id(file_id)
    canonical = make_file_id(label, rel)
    entry = _find_manifest_entry(manifest, canonical)
    if entry is not None:
        entry["file_id"] = canonical
        entry["file"] = rel
        entry["title"] = title
        entry["source"] = source
        entry["ingested"] = ingested
        if reset_compiled:
            entry["compiled"] = False
        _write_manifest(context_dir, manifest)
        return
    manifest.append(
        {
            "file_id": canonical,
            "file": rel,
            "title": title,
            "source": source,
            "ingested": ingested,
            "compiled": False,
        }
    )
    _write_manifest(context_dir, manifest)


def apply_raw_frontmatter_to_text(
    text: str,
    *,
    source: str,
    tags: list[str],
    doc_type: str,
    title: str | None = None,
    fallback_title: str = "Untitled",
    force: bool = False,
) -> tuple[str | None, str, str | None]:
    """Prepend km-agent raw frontmatter when missing (or when ``force``).

    Returns ``(new_text, resolved_title, skip_reason)``. ``new_text`` is ``None`` when skipped.
    """
    if has_yaml_frontmatter(text) and not force:
        return None, "", "already has YAML frontmatter"

    body = strip_yaml_frontmatter(text) if force and has_yaml_frontmatter(text) else text
    resolved_title = title or title_from_markdown(body, fallback_stem=fallback_title)
    front = _build_frontmatter(resolved_title, source, tags, doc_type)
    new_text = front + body.lstrip("\n")
    if not new_text.endswith("\n"):
        new_text += "\n"
    return new_text, resolved_title, None


def _context_dir_from_raw(raw_dir: Path) -> Path:
    """Derive context dir: parent of ``raw/``, else the given path itself."""
    raw = Path(raw_dir).resolve()
    return raw.parent if raw.name == "raw" else raw


def _do_ingest_url(raw_dir: Path, url: str, title: str, tags: list[str] | None = None, doc_type: str = "article") -> str:
    """Core ingest-URL logic (callable directly and via @tool wrapper)."""

    slug = _slugify(title)
    filename = f"{slug}.md"
    file_path = raw_dir / filename
    frontmatter = _build_frontmatter(title, url, tags or [], doc_type)

    # Fetch page text over HTTP (bounded — keeps local LLM context small)
    extracted = ""
    fetch_error = ""
    try:
        extracted = _fetch_url_text(url, get_ingest_max_chars())
    except Exception as e:
        fetch_error = str(e)

    if extracted:
        file_path.write_text(frontmatter + extracted + "\n")
        status = f"Ingested with content: {filename} ({len(extracted)} chars)"
    else:
        stub = (
            f"Source: {url}\n\n"
            f"*(Content fetch failed: {fetch_error or 'empty response'}. "
            f"Stub saved — use ingest_text with a summary.)*"
        )
        file_path.write_text(frontmatter + stub + "\n")
        status = f"Ingested stub: {filename} (fetch failed)"

    context_dir = _context_dir_from_raw(raw_dir)
    append_manifest_entry(
        context_dir,
        make_file_id(INGESTED_LABEL, filename),
        title,
        url,
        reset_compiled=True,
    )

    return status


def sanitize_raw_export_filename(filename: str) -> str:
    """Return a basename-only ``*.md`` name safe to write under ``raw/``.

    Rejects empty names, ``..``, and absolute/parent path segments.
    Appends ``.md`` when missing.
    """
    raw = (filename or "").strip()
    if not raw:
        raise ValueError("filename is required")
    name = Path(raw).name
    if not name or name in (".", "..") or name.startswith("."):
        raise ValueError("invalid filename")
    if "/" in name or "\\" in name or ".." in name:
        raise ValueError("invalid filename")
    if not name.lower().endswith(".md"):
        name = f"{name}.md"
    return name


def ingest_text_as_file(
    raw_dir: Path,
    filename: str,
    content: str,
    *,
    title: str | None = None,
    source: str = "user",
    tags: list[str] | None = None,
    doc_type: str = "notes",
) -> str:
    """Write ``content`` to ``raw_dir/filename`` with frontmatter and update the manifest.

    Honors the given filename (after sanitization). Overwrites an existing file and
    resets ``compiled`` on that manifest row in ``context/.manifest.json``.
    """
    raw_path = Path(raw_dir)
    raw_path.mkdir(parents=True, exist_ok=True)
    safe = sanitize_raw_export_filename(filename)
    resolved_title = (title or Path(safe).stem).strip() or Path(safe).stem
    file_path = raw_path / safe
    frontmatter = _build_frontmatter(resolved_title, source, tags or [], doc_type)
    body = content if content.endswith("\n") else f"{content}\n"
    file_path.write_text(frontmatter + body, encoding="utf-8")
    context_dir = _context_dir_from_raw(raw_path)
    append_manifest_entry(
        context_dir,
        make_file_id(INGESTED_LABEL, safe),
        resolved_title,
        source,
        reset_compiled=True,
    )
    return f"Ingested: {safe} ({len(content)} chars)"


def _do_ingest_text(
    raw_dir: Path, title: str, content: str, source: str = "user", tags: list[str] | None = None, doc_type: str = "notes"
) -> str:
    """Core ingest-text logic (callable directly and via @tool wrapper)."""
    slug = _slugify(title)
    filename = f"{slug}.md"
    return ingest_text_as_file(
        raw_dir,
        filename,
        content,
        title=title,
        source=source,
        tags=tags,
        doc_type=doc_type,
    )



def create_ingest_tools(raw_dir: Path) -> list:
    """Create ingest tools bound to ``raw/`` and the shared ``context/.manifest.json``.

    Args:
        raw_dir: Path to ``context/raw/`` (context is ``raw_dir.parent``).

    Returns:
        List of tool functions.
    """
    context_dir = _context_dir_from_raw(raw_dir)

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
        """Read the shared context manifest (studies + ingested) and compile status.

        Returns:
            JSON string of the manifest entries.
        """
        manifest = _read_manifest(context_dir)
        if not manifest:
            return "No documents ingested yet. The manifest is empty."
        return json.dumps(manifest, indent=2)

    @tool
    def update_manifest_compiled(filename: str) -> str:
        """Mark a document as compiled in the shared context manifest.

        Call this after successfully compiling a raw document into wiki articles.

        Args:
            filename: ``file_id`` (``ingested:name.md`` or ``studies:path.md``), or a bare
                raw filename (treated as ``ingested:…``).

        Returns:
            Confirmation message.
        """
        key = filename.strip()
        if ":" not in key:
            key = make_file_id(INGESTED_LABEL, key)
        if mark_manifest_compiled(context_dir, key):
            return f"Marked as compiled: {key}"
        return f"Not found in manifest: {key}"

    @tool
    def sync_raw_manifest_from_disk() -> str:
        """Rebuild ``ingested:*`` rows in context/.manifest.json from raw/*.md frontmatter.

        Use when raw markdown was added or restored without going through ingest_url /
        ingest_text. Preserves other labels (e.g. studies).
        """
        return sync_manifest_from_raw_markdown(context_dir, label=INGESTED_LABEL, raw_dir=raw_dir)

    return [ingest_url, ingest_text, read_manifest, update_manifest_compiled, sync_raw_manifest_from_disk]


def create_compiler_manifest_tools(
    context_dir: Path, raw_roots: Sequence[tuple[str, Path]]
) -> tuple[object, object]:
    """``read_manifest`` / ``update_manifest_compiled`` over the shared ``context/.manifest.json``.

    ``raw_roots`` is kept for API compatibility; entries are keyed by ``file_id``
    (``label:relpath``).
    """

    ctx = context_dir.resolve()
    _ = raw_roots  # content lives under each root; tracking is unified under context

    @tool
    def read_manifest() -> str:
        """Read the shared context manifest (all raw roots). Each row includes ``file_id``."""
        manifest = _read_manifest(ctx)
        if not manifest:
            return "No documents ingested yet. The manifest is empty."
        # Ensure file_id is present for agents
        rows: list[dict] = []
        for entry in manifest:
            row = dict(entry)
            fid = _entry_file_id(row)
            if fid:
                row["file_id"] = fid
            rows.append(row)
        return json.dumps(rows, indent=2)

    @tool
    def update_manifest_compiled(filename: str) -> str:
        """Mark a document compiled. Prefer ``file_id`` from read_manifest (``label:relpath``)."""
        key = filename.strip()
        if ":" not in key:
            # Ambiguous bare name: try ingested: first, then any matching file field
            ingested_key = make_file_id(INGESTED_LABEL, key)
            if mark_manifest_compiled(ctx, ingested_key):
                return f"Marked as compiled: {ingested_key}"
            if mark_manifest_compiled(ctx, key):
                return f"Marked as compiled: {key}"
            return (
                f"Not found in manifest: {key}. "
                "Use file_id label:relpath from read_manifest when multiple raw roots exist."
            )
        if mark_manifest_compiled(ctx, key):
            return f"Marked as compiled: {key}"
        return f"Not found in manifest: {key}"

    return read_manifest, update_manifest_compiled
