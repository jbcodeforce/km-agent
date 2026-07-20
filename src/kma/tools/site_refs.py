"""Load trusted web site references for research bias (web_site_ref.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from agno.tools import tool


@dataclass(frozen=True)
class WebSiteRef:
    """One trusted source entry from web_site_ref.json."""

    name: str
    url: str
    description: str


def _parse_site_entry(raw: object, index: int) -> WebSiteRef:
    if not isinstance(raw, dict):
        raise ValueError(f"site entry {index} must be an object")
    name = raw.get("name")
    url = raw.get("url")
    description = raw.get("description")
    missing = [k for k, v in (("name", name), ("url", url), ("description", description)) if not v or not str(v).strip()]
    if missing:
        raise ValueError(f"site entry {index} missing required field(s): {', '.join(missing)}")
    return WebSiteRef(
        name=str(name).strip(),
        url=str(url).strip(),
        description=str(description).strip(),
    )


def load_web_site_refs(path: Path) -> list[WebSiteRef]:
    """Load site references from JSON (top-level array or ``{\"sites\": [...]}``)."""
    p = path.resolve()
    if not p.is_file():
        raise FileNotFoundError(f"web site refs file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {p}: {exc}") from exc

    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict) and isinstance(data.get("sites"), list):
        entries = data["sites"]
    else:
        raise ValueError(f"{p}: expected a JSON array or object with 'sites' array")

    return [_parse_site_entry(entry, i) for i, entry in enumerate(entries)]


def resolve_site_refs_path(
    context_dir: Path,
    site_refs_path: Path | None = None,
) -> Path | None:
    """Return explicit path if given, else default ``context/web_site_ref.json`` when present."""
    if site_refs_path is not None:
        return site_refs_path.resolve()
    default = context_dir.resolve() / "web_site_ref.json"
    return default if default.is_file() else None


def load_site_refs_for_context(
    context_dir: Path,
    site_refs_path: Path | None = None,
) -> list[WebSiteRef]:
    """Load site refs from explicit path or context default; empty list if none configured."""
    resolved = resolve_site_refs_path(context_dir, site_refs_path)
    if resolved is None:
        return []
    return load_web_site_refs(resolved)


def format_site_refs_for_prompt(refs: list[WebSiteRef]) -> str:
    """Format trusted sites as a bullet list for researcher prompts."""
    if not refs:
        return ""
    lines = ["## Trusted sources (prioritize these when searching and ingesting)"]
    for ref in refs:
        lines.append(f"- **{ref.name}** — {ref.url}")
        lines.append(f"  Use when: {ref.description}")
    return "\n".join(lines)


def create_read_web_site_refs_tool(context_dir: Path | None = None):
    """Agno tool: read and format web_site_ref.json for the Researcher."""
    ctx = (context_dir or Path.cwd()).resolve()
    default_path = ctx / "web_site_ref.json"

    @tool
    def read_web_site_refs(path: str = "") -> str:
        """Read trusted web site references from web_site_ref.json.

        Use before web_search to bias toward official or curated sources.
        When ``path`` is empty, reads ``<context>/web_site_ref.json``.

        Args:
            path: Optional path to the JSON file (absolute or relative to context).

        Returns:
            Formatted list of trusted sites with URLs and usage hints.
        """
        target = Path(path).expanduser() if path.strip() else default_path
        if not target.is_absolute():
            target = (ctx / target).resolve()
        refs = load_web_site_refs(target)
        if not refs:
            return f"No site entries in {target}"
        return format_site_refs_for_prompt(refs)

    return read_web_site_refs
