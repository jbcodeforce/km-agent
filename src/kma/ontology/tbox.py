"""Load and expose the km-agent TBox."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph


def default_tbox_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "tbox.ttl"


def load_tbox(tbox_path: Path | None = None) -> Graph:
    g = Graph()
    path = tbox_path or default_tbox_path()
    if path.exists():
        g.parse(path, format="turtle")
    return g


def ensure_context_tbox(ontology_dir: Path) -> Path:
    """Copy bundled TBox to context/ontology/tbox.ttl if missing."""
    ontology_dir.mkdir(parents=True, exist_ok=True)
    dest = ontology_dir / "tbox.ttl"
    if not dest.exists():
        bundled = default_tbox_path()
        dest.write_text(bundled.read_text(encoding="utf-8"), encoding="utf-8")
    return dest
