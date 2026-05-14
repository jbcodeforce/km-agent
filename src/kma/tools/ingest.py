"""Ingest tools — fetch URLs and save text to raw/ with frontmatter."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from agno.tools import tool



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
    from kma.config import PARALLEL_API_KEY

    slug = _slugify(title)
    filename = f"{slug}.md"
    file_path = raw_dir / filename
    frontmatter = _build_frontmatter(title, url, tags or [], doc_type)

    # Try to fetch content via Parallel
    extracted = ""
    if PARALLEL_API_KEY:
        try:
            from parallel import Parallel

            client = Parallel(api_key=PARALLEL_API_KEY)
            result = client.beta.extract(urls=[url], full_content=True)
            if result and result.results:
                r = result.results[0]
                extracted = r.full_content or ""
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
    def ingest_url(url: str, title: str, tags: list[str] | None = None, doc_type: str = "article") -> str:
        """Ingest a URL into the knowledge base raw/ directory.

        Fetches page content via Parallel (if configured) and saves as a
        markdown file with YAML frontmatter in raw/. Falls back to
        a stub if Parallel is not configured or extraction fails.

        Args:
            url: The source URL.
            title: A descriptive title for the document.
            tags: Optional list of topic tags (e.g. ["rag", "retrieval"]).
            doc_type: Document type: paper, article, repo, notes, transcript, image.

        Returns:
            Confirmation with the file path and content status.
        """
        return _do_ingest_url(raw_dir, url, title, tags, doc_type)

    @tool
    def ingest_text(
        title: str, content: str, source: str = "user", tags: list[str] | None = None, doc_type: str = "notes"
    ) -> str:
        """Ingest text content into the knowledge base raw/ directory.

        Saves text as a markdown file with YAML frontmatter in raw/.
        Use this for clipboard content, meeting notes, manually provided text,
        or content fetched from web research.

        Args:
            title: A descriptive title for the document.
            content: The markdown content to save.
            source: Where the content came from (URL, "user", "clipboard", etc.).
            tags: Optional list of topic tags.
            doc_type: Document type: paper, article, repo, notes, transcript, image.

        Returns:
            Confirmation with the file path.
        """
        return _do_ingest_text(raw_dir, title, content, source, tags, doc_type)

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
        manifest = _read_manifest(raw_dir)
        for entry in manifest:
            if entry["file"] == filename:
                entry["compiled"] = True
                _write_manifest(raw_dir, manifest)
                return f"Marked as compiled: {filename}"
        return f"Not found in manifest: {filename}"

    return [ingest_url, ingest_text, read_manifest, update_manifest_compiled]


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
            for entry in manifest:
                if entry.get("file") == rel:
                    entry["compiled"] = True
                    _write_manifest(raw_home, manifest)
                    return f"Marked as compiled: {key}"
            return f"Not found in manifest: {key}"
        if len(roots) == 1:
            raw_home = roots[0][1]
            manifest = _read_manifest(raw_home)
            for entry in manifest:
                if entry.get("file") == key:
                    entry["compiled"] = True
                    _write_manifest(raw_home, manifest)
                    return f"Marked as compiled: {key}"
            return f"Not found in manifest: {key}"
        # multi-root but caller passed bare file — ambiguous
        return (
            f"Not found in manifest: {key}. "
            "Use file_id label:relpath from read_manifest when multiple raw roots exist."
        )

    return read_manifest, update_manifest_compiled
