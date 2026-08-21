"""Copy and rewrite every local resource cited by an installed skill."""

from pathlib import Path, PurePosixPath
import re
from typing import Iterable

from install_lib.plugin_metadata import Plugin, Skill


RESOURCE = re.compile(r"(?<![\w:/.-])(?P<path>(?:(?:\.\.?/)+)?(?:plays|templates|data)(?:/[A-Za-z0-9_.*{}\[\],<>#-]+)*)")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
DYNAMIC = re.compile(r"[<>{}\[\]*#]")


def _repo_root(plugin: Plugin) -> Path:
    return plugin.path.parent.parent


def _raw_references(text: str) -> tuple[str, ...]:
    values: set[str] = set()
    for match in CODE_SPAN.finditer(text):
        values.update(found.group("path") for found in RESOURCE.finditer(match.group(1)))
    for match in MARKDOWN_LINK.finditer(text):
        values.update(found.group("path") for found in RESOURCE.finditer(match.group(1)))
    return tuple(sorted(values, key=lambda value: (-len(value), value)))


def _dynamic_root(raw: str, source: Path, plugin: Plugin) -> Path | None:
    prefix = DYNAMIC.split(raw, maxsplit=1)[0].rstrip("/")
    base = source.parent if raw.startswith(".") else plugin.path
    candidate = (base / prefix).resolve()
    while not candidate.exists() and candidate != plugin.path:
        candidate = candidate.parent
    return candidate if candidate.exists() and candidate != plugin.path else None


def _resolve(raw: str, source: Path, plugin: Plugin) -> Path:
    base = source.parent if raw.startswith(".") else plugin.path
    candidate = (base / raw).resolve()
    if candidate.exists():
        return candidate

    if not raw.startswith(".") and raw.startswith("data/"):
        candidate = (_repo_root(plugin) / raw).resolve()
        if candidate.exists():
            return candidate
        if DYNAMIC.search(raw) or "XXX" in raw:
            prefix = (DYNAMIC.split(raw, maxsplit=1)[0] if DYNAMIC.search(raw) else raw.split("XXX", 1)[0]).rstrip("/")
            candidate = (_repo_root(plugin) / prefix).resolve()
            while not candidate.exists() and candidate != _repo_root(plugin):
                candidate = candidate.parent
            if candidate.is_dir():
                return candidate

    parts = PurePosixPath(raw).parts
    if "templates" in parts:
        candidate = plugin.path.joinpath("templates", *parts[parts.index("templates") + 1 :])
        if candidate.exists():
            return candidate

    if DYNAMIC.search(raw):
        candidate = _dynamic_root(raw, source, plugin)
        roots = (plugin.path.resolve(), (_repo_root(plugin) / "data").resolve())
        if candidate is not None and any(candidate.is_relative_to(root) for root in roots if root.exists()):
            return candidate

    raise ValueError(f"{source}: unresolved local resource {raw!r}")


def _references(source: Path, plugin: Plugin) -> tuple[tuple[str, Path], ...]:
    text = source.read_text(encoding="utf-8")
    return tuple((raw, _resolve(raw, source, plugin)) for raw in _raw_references(text))


def _is_dataset(path: Path, plugin: Plugin) -> bool:
    return path.is_relative_to(plugin.path / "data") or path.is_relative_to(_repo_root(plugin) / "data")


def _files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from (candidate for candidate in sorted(path.rglob("*")) if candidate.is_file())


def _destination(path: Path, plugin: Plugin) -> PurePosixPath:
    path = path.resolve()
    plugin_root = plugin.path.resolve()
    repo_data = (_repo_root(plugin) / "data").resolve()
    if path.is_relative_to(plugin_root):
        return PurePosixPath("references") / PurePosixPath(path.relative_to(plugin_root).as_posix())
    if path.is_relative_to(repo_data):
        return PurePosixPath("references/data") / PurePosixPath(path.relative_to(repo_data).as_posix())
    raise ValueError(f"Resource {path} is outside the plugin and repository data trees")


def _support_paths(skill: Skill) -> tuple[Path, ...]:
    pending = [skill.path]
    seen: set[Path] = set()
    support: set[Path] = set()
    while pending:
        document = pending.pop()
        if document in seen:
            continue
        seen.add(document)
        for _, resolved in _references(document, skill.plugin):
            support.add(resolved)
            if resolved.is_file() and resolved.suffix == ".md" and not _is_dataset(resolved, skill.plugin):
                pending.append(resolved)
            elif resolved.is_dir() and not _is_dataset(resolved, skill.plugin):
                pending.extend(resolved.rglob("*.md"))
    return tuple(sorted(support))


def installed_files(skill: Skill) -> dict[PurePosixPath, bytes]:
    """Return the complete standalone skill, including cited datasets."""
    support = _support_paths(skill)
    documents = [skill.path, *(path for path in support if path.is_file() and not _is_dataset(path, skill.plugin))]
    files: dict[PurePosixPath, bytes] = {}

    for source in documents:
        text = source.read_text(encoding="utf-8")
        for raw, resolved in _references(source, skill.plugin):
            replacement = _destination(resolved, skill.plugin).as_posix()
            text = text.replace(raw, replacement if resolved.is_file() else replacement + "/")
        destination = PurePosixPath("SKILL.md") if source == skill.path else _destination(source, skill.plugin)
        files[destination] = text.encode("utf-8")

    for source in support:
        for file_path in _files(source):
            destination = _destination(file_path, skill.plugin)
            if destination not in files:
                files[destination] = file_path.read_bytes()

    for destination, content in files.items():
        if destination.suffix != ".md":
            continue
        for raw in _raw_references(content.decode("utf-8")):
            if not raw.startswith("references/"):
                continue
            candidate = PurePosixPath(raw.rstrip("/"))
            if candidate not in files and not any(path.is_relative_to(candidate) for path in files):
                raise ValueError(f"Installed {destination} references absent resource {raw}")
    return files
