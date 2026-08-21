"""Build one shared plays, templates, and data tree for all skills."""

from pathlib import PurePosixPath
import posixpath
import re
from typing import Iterable

from install_lib.plugin_metadata import Skill


RESOURCE = re.compile(r"(?<![\w:/.-])(?P<path>(?:(?:\.\.?/)+)?(?:plays|templates|data)(?:/[A-Za-z0-9_.*{}\[\],<>#-]+)*)")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
DYNAMIC = re.compile(r"[<>{}\[\]*#]|XXX")
RESOURCE_DIRECTORIES = ("plays", "templates", "data")


def _references(text: str) -> tuple[str, ...]:
    values: set[str] = set()
    for match in CODE_SPAN.finditer(text):
        values.update(found.group("path") for found in RESOURCE.finditer(match.group(1)))
    for match in MARKDOWN_LINK.finditer(text):
        values.update(found.group("path") for found in RESOURCE.finditer(match.group(1)))
    return tuple(sorted(values, key=lambda value: (-len(value), value)))


def _add(files: dict[PurePosixPath, bytes], destination: PurePosixPath, content: bytes) -> None:
    existing = files.get(destination)
    if existing is not None and existing != content:
        raise ValueError(f"Conflicting shared resource {destination}")
    files[destination] = content


def _rewrite(source_name: str, text: str) -> str:
    if source_name == "SKILL.md":
        return text.replace("../../plays/", "plays/").replace("../../templates/", "templates/")
    if source_name.startswith("plays/"):
        return text.replace("../../templates/", "../templates/")
    return text


def _validate(files: dict[PurePosixPath, bytes], resource_dir: PurePosixPath) -> None:
    directories = {parent for path in files for parent in path.parents}
    for source, content in files.items():
        if source.suffix != ".md":
            continue
        for raw in _references(content.decode("utf-8")):
            if raw.startswith("."):
                candidate = PurePosixPath(posixpath.normpath((source.parent / raw).as_posix()))
            else:
                candidate = resource_dir / raw.rstrip("/")
            dynamic_part = next((part for part in candidate.parts if DYNAMIC.search(part)), None)
            if dynamic_part is not None:
                candidate = PurePosixPath(*candidate.parts[:candidate.parts.index(dynamic_part)])
            if candidate not in files and candidate not in directories:
                raise ValueError(f"Installed {source} references absent resource {raw}")


def installed_bundle(skills: Iterable[Skill], resource_dir: PurePosixPath) -> dict[PurePosixPath, bytes]:
    """Return every skill and one shared copy of its supporting resources."""
    selected = tuple(skills)
    files: dict[PurePosixPath, bytes] = {}
    for skill in selected:
        text = _rewrite("SKILL.md", skill.path.read_text(encoding="utf-8"))
        files[PurePosixPath(skill.name) / "SKILL.md"] = text.encode("utf-8")

    plugins = {skill.plugin.path.resolve(): skill.plugin for skill in selected}.values()
    for plugin in plugins:
        for directory_name in RESOURCE_DIRECTORIES:
            directory = plugin.path / directory_name
            if not directory.is_dir():
                continue
            for source in sorted(path for path in directory.rglob("*") if path.is_file()):
                relative = PurePosixPath(source.relative_to(directory).as_posix())
                destination = resource_dir / directory_name / relative
                content = source.read_bytes()
                if source.suffix == ".md":
                    name = f"{directory_name}/{relative.as_posix()}"
                    content = _rewrite(name, content.decode("utf-8")).encode("utf-8")
                # ASVS 5.3.2: destinations use fixed directory names and
                # canonical source-relative paths, never user-provided paths.
                _add(files, destination, content)

    repo_data = next(iter(plugins)).path.resolve().parent.parent / "data"
    for source in sorted(path for path in repo_data.rglob("*") if path.is_file()):
        relative = PurePosixPath(source.relative_to(repo_data).as_posix())
        _add(files, resource_dir / "data" / relative, source.read_bytes())

    _validate(files, resource_dir)
    return files


def dataset_file_count(files: Iterable[PurePosixPath], resource_dir: PurePosixPath) -> int:
    """Count unique files under the shared data directory."""
    return sum(path.is_relative_to(resource_dir / "data") for path in files)
