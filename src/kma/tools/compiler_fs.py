"""Split-root filesystem tools for the Compiler when raw/ spans multiple disk locations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Sequence

from agno.tools import tool
from agno.tools._local_file_utils import DEFAULT_EXCLUDE_PATTERNS, path_matches_exclude


def use_labelled_raw_paths(raw_roots: Sequence[tuple[str, Path]], context_dir: Path) -> bool:
    """True if raw paths must use ``raw/<label>/...`` (multi-root or external single raw)."""
    ctx = context_dir.resolve()
    default_raw = (ctx / "raw").resolve()
    if len(raw_roots) != 1:
        return True
    _label, only = raw_roots[0]
    return only.resolve() != default_raw


def _is_under(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _excluded(path: Path, base: Path) -> bool:
    return path_matches_exclude(path, base, DEFAULT_EXCLUDE_PATTERNS)


def create_compiler_file_tools(context_dir: Path, raw_roots: Sequence[tuple[str, Path]]) -> list:
    """File tools: ``wiki/...`` under ``context_dir``; ``raw/<label>/...`` per root (or legacy ``raw/...``)."""

    ctx = context_dir.resolve()
    roots_list: list[tuple[str, Path]] = [(str(label), Path(root).resolve()) for label, root in raw_roots]
    root_by_label = {lab: r for lab, r in roots_list}
    labelled = use_labelled_raw_paths(roots_list, ctx)
    default_raw = (ctx / "raw").resolve()
    single_raw = roots_list[0][1] if len(roots_list) == 1 else None

    def _resolve(file_name: str) -> tuple[bool, Path]:
        name = file_name.replace("\\", "/").lstrip("/")
        if name.startswith("wiki/"):
            p = (ctx / name).resolve()
            if _is_under(ctx, p):
                return True, p
            return False, ctx
        if name.startswith("raw/"):
            rest = name[len("raw/") :]
            if labelled:
                m = re.match(r"([^/]+)/(.+)$", rest)
                if not m:
                    return False, ctx
                lab, rel = m.group(1), m.group(2)
                base = root_by_label.get(lab)
                if base is None:
                    return False, ctx
                p = (base / rel).resolve()
                if _is_under(base, p):
                    return True, p
                return False, ctx
            if single_raw is not None:
                p = (single_raw / rest).resolve()
                if _is_under(single_raw, p):
                    return True, p
                return False, ctx
        return False, ctx

    def _virtual_raw_path(physical: Path, anchor: Path, label: str) -> str:
        rel = physical.resolve().relative_to(anchor).as_posix()
        if labelled:
            return f"raw/{label}/{rel}" if rel != "." else f"raw/{label}"
        return f"raw/{rel}" if rel != "." else "raw"

    @tool
    def read_file(file_name: str, encoding: str = "utf-8") -> str:
        """Read a file under wiki/ or raw/. Use raw/<label>/path when multiple raw roots exist."""
        try:
            safe, path = _resolve(file_name)
            if not safe or not path.is_file():
                return "Error reading file"
            return path.read_text(encoding=encoding)
        except Exception as e:
            return f"Error reading file: {e}"

    @tool
    def save_file(contents: str, file_name: str, overwrite: bool = True, encoding: str = "utf-8") -> str:
        """Save content to a file under wiki/ (raw/ is read-only for the compiler)."""
        try:
            name = file_name.replace("\\", "/").lstrip("/")
            if not name.startswith("wiki/"):
                return "Error saving file: only wiki/ paths are writable"
            safe, path = _resolve(file_name)
            if not safe:
                return "Error saving file"
            if path.exists() and not path.is_dir() and not overwrite:
                return f"File {file_name} already exists"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding=encoding)
            return str(file_name)
        except Exception as e:
            return f"Error saving to file: {e}"

    @tool
    def list_files(directory: str = ".") -> str:
        """List entries in wiki/ or raw/ (use raw/<label>/... when multiple raw roots)."""
        try:
            d = directory.replace("\\", "/").strip()
            if d in (".", "", "wiki"):
                base = ctx / "wiki"
                if not base.is_dir():
                    return "[]"
                out = [
                    str((base / f).relative_to(ctx)).replace("\\", "/")
                    for f in sorted(base.iterdir(), key=lambda p: p.name)
                    if not _excluded(base / f, ctx)
                ]
                return json.dumps(out, indent=2)
            if d.startswith("wiki/"):
                base = (ctx / d).resolve()
                wroot = (ctx / "wiki").resolve()
                if not (base == wroot or _is_under(wroot, base)):
                    return "[]"
                if not base.is_dir():
                    return "[]"
                out = [
                    str((base / f).relative_to(ctx)).replace("\\", "/")
                    for f in sorted(base.iterdir(), key=lambda p: p.name)
                    if not _excluded(base / f, ctx)
                ]
                return json.dumps(out, indent=2)
            if d == "raw" or d.startswith("raw/"):
                if labelled:
                    tail = d[4:].lstrip("/") if d.startswith("raw/") else ""
                    if not tail:
                        return json.dumps([f"raw/{n}" for n in sorted(root_by_label)], indent=2)
                    parts = tail.split("/", 1)
                    lab = parts[0]
                    sub = parts[1] if len(parts) > 1 else ""
                    anchor = root_by_label.get(lab)
                    if anchor is None:
                        return "[]"
                    base = (anchor / sub).resolve() if sub else anchor
                    if not (_is_under(anchor, base) or base == anchor):
                        return "[]"
                else:
                    tail = d[4:].lstrip("/") if d.startswith("raw/") else ""
                    base = (default_raw / tail).resolve() if tail else default_raw
                    if not (_is_under(default_raw, base) or base == default_raw):
                        return "[]"
                if not base.is_dir():
                    return "[]"
                out: list[str] = []
                for child in sorted(base.iterdir(), key=lambda p: p.name):
                    if _excluded(child, base):
                        continue
                    if labelled:
                        lab = next(l for l, r in roots_list if child.resolve() == r or _is_under(r, child.resolve()))
                        anchor = root_by_label[lab]
                        out.append(_virtual_raw_path(child, anchor, lab))
                    else:
                        out.append(_virtual_raw_path(child, default_raw, ""))
                return json.dumps(out, indent=2)
            return "[]"
        except Exception as e:
            return f"Error listing files: {e}"

    @tool
    def search_files(pattern: str) -> str:
        """Glob under wiki/ and each raw root; returns paths usable with read_file."""
        try:
            if not pattern or not pattern.strip():
                return "Error: Pattern cannot be empty"
            matches: list[str] = []
            wiki_root = ctx / "wiki"
            if wiki_root.is_dir():
                for p in wiki_root.glob(pattern):
                    if p.is_file() and not _excluded(p, ctx) and _is_under(ctx, p):
                        matches.append(str(p.relative_to(ctx)).replace("\\", "/"))
            for lab, rroot in roots_list:
                if not rroot.is_dir():
                    continue
                for p in rroot.glob(pattern):
                    if p.is_file() and not _excluded(p, rroot) and _is_under(rroot, p):
                        matches.append(_virtual_raw_path(p, rroot, lab))
            return json.dumps({"pattern": pattern, "matches_found": len(matches), "files": sorted(set(matches))}, indent=2)
        except Exception as e:
            return f"Error searching files: {e}"

    return [read_file, save_file, list_files, search_files]
