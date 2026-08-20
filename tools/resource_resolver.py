"""Pure install-time materialization of standalone skills.

Canonical skills retain their authored references. This module derives a
closure from those references and rewrites only the destination copy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import hashlib
import re
from typing import Iterable, Literal

from plugin_metadata import PluginMeta, SkillRecord


ReferenceClass = Literal["local_file", "local_directory", "dynamic_local_subtree", "external", "unresolved_local"]
RESOURCE = re.compile(r"(?<![\w:/.-])(?P<path>(?:(?:\.\.?/)+)?(?:plays|templates|data)(?:/[A-Za-z0-9_.*{}\[\],<>#-]+)*)")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
DYNAMIC = re.compile(r"[<>{}\[\]*#]")


class ResourceResolutionError(ValueError):
    """Raised for local-looking references without an owned source resource."""


@dataclass(frozen=True)
class ResourceReference:
    source_file: Path
    raw: str
    classification: ReferenceClass
    resolved_path: Path | None


@dataclass(frozen=True)
class Bundle:
    source_file: Path
    plugin: PluginMeta
    references: tuple[ResourceReference, ...]
    support_paths: tuple[Path, ...]
    includes_data: bool
    data_hashes: dict[str, str]


@dataclass(frozen=True)
class InstalledForm:
    """Destination-relative files and a transformed root skill document."""

    skill: SkillRecord
    files: dict[PurePosixPath, bytes]
    text: str
    bundle: Bundle
    with_data: bool

    @property
    def data_file_count(self) -> int:
        return sum(1 for path in self.files if path.parts[:2] == ("references", "data"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repository_root(plugin: PluginMeta) -> Path:
    return plugin.path.parent.parent


def _source_base(raw: str, source: Path, plugin: PluginMeta) -> Path:
    return source.parent if raw.startswith(".") else plugin.path


def _dynamic_root(raw: str, source: Path, plugin: PluginMeta) -> Path | None:
    prefix = DYNAMIC.split(raw, maxsplit=1)[0].rstrip("/")
    candidate = (_source_base(raw, source, plugin) / prefix).resolve()
    while not candidate.exists() and candidate != plugin.path:
        candidate = candidate.parent
    return candidate if candidate.exists() and candidate != plugin.path else None


def classify_reference(raw: str, source_file: Path, plugin: PluginMeta) -> ResourceReference:
    """Classify one known resource-shaped reference without changing source text."""
    if raw.startswith(("http://", "https://")):
        return ResourceReference(source_file, raw, "external", None)
    candidate = (_source_base(raw, source_file, plugin) / raw).resolve()
    source_roots = (plugin.path.resolve(), _repository_root(plugin) / "data")
    if candidate.is_file():
        return ResourceReference(source_file, raw, "local_file", candidate)
    if candidate.is_dir():
        return ResourceReference(source_file, raw, "local_directory", candidate)
    # Templates cite the repository-level OpenCRE research bundle with the same
    # concise ``data/...`` spelling used for plugin-local datasets.
    if not raw.startswith(".") and raw.startswith("data/"):
        repository_candidate = (_repository_root(plugin) / raw).resolve()
        if repository_candidate.is_file():
            return ResourceReference(source_file, raw, "local_file", repository_candidate)
        if repository_candidate.is_dir():
            return ResourceReference(source_file, raw, "local_directory", repository_candidate)
        if DYNAMIC.search(raw) or "XXX" in raw:
            prefix = (DYNAMIC.split(raw, maxsplit=1)[0] if DYNAMIC.search(raw) else raw.split("XXX", 1)[0]).rstrip("/")
            dynamic_candidate = (_repository_root(plugin) / prefix).resolve()
            repository_root = _repository_root(plugin).resolve()
            while not dynamic_candidate.exists() and dynamic_candidate != repository_root:
                dynamic_candidate = dynamic_candidate.parent
            if dynamic_candidate.is_dir():
                return ResourceReference(source_file, raw, "dynamic_local_subtree", dynamic_candidate)
    # A few runbooks retain a skill-relative ``../../templates`` link. Once
    # the referenced runbook is scanned from its plugin-level location, the
    # same authored link names the plugin template by suffix.
    normalized = PurePosixPath(raw)
    if "templates" in normalized.parts:
        suffix = normalized.parts[normalized.parts.index("templates") + 1 :]
        fallback = plugin.path.joinpath("templates", *suffix)
        if fallback.is_file():
            return ResourceReference(source_file, raw, "local_file", fallback)
        if fallback.is_dir():
            return ResourceReference(source_file, raw, "local_directory", fallback)
    if DYNAMIC.search(raw):
        dynamic_root = _dynamic_root(raw, source_file, plugin)
        if dynamic_root is not None and any(dynamic_root.is_relative_to(root.resolve()) for root in source_roots if root.exists()):
            return ResourceReference(source_file, raw, "dynamic_local_subtree", dynamic_root)
    return ResourceReference(source_file, raw, "unresolved_local", None)


def _raw_references(text: str) -> tuple[str, ...]:
    values: set[str] = set()
    for match in CODE_SPAN.finditer(text):
        values.update(value.group("path") for value in RESOURCE.finditer(match.group(1)))
    for match in MARKDOWN_LINK.finditer(text):
        values.update(value.group("path") for value in RESOURCE.finditer(match.group(1)))
    return tuple(sorted(values, key=lambda value: (-len(value), value)))


def scan_references(source_file: Path, plugin: PluginMeta) -> tuple[ResourceReference, ...]:
    text = source_file.read_text(encoding="utf-8")
    return tuple(classify_reference(raw, source_file, plugin) for raw in _raw_references(text))


def scan_corpus(repo_root: Path) -> tuple[ResourceReference, ...]:
    """Return a deterministic classified snapshot of canonical plugin Markdown."""
    from plugin_metadata import discover_repository

    inventory = discover_repository(repo_root)
    result: list[ResourceReference] = []
    for skill in inventory.skills:
        result.extend(scan_references(skill.path, skill.plugin))
    for agent in inventory.agents:
        result.extend(scan_references(agent.path, agent.plugin))
    return tuple(result)


def _is_plugin_data(path: Path, plugin: PluginMeta) -> bool:
    return path.is_relative_to(plugin.path / "data")


def _is_research_data(path: Path, plugin: PluginMeta) -> bool:
    return path.is_relative_to(_repository_root(plugin) / "data")


def _is_dataset(path: Path, plugin: PluginMeta) -> bool:
    return _is_plugin_data(path, plugin) or _is_research_data(path, plugin)


def _iter_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from (candidate for candidate in sorted(path.rglob("*")) if candidate.is_file())


def _reference_destination(path: Path, plugin: PluginMeta) -> PurePosixPath:
    plugin_root = plugin.path.resolve()
    repo_data = (_repository_root(plugin) / "data").resolve()
    if path.is_relative_to(plugin_root):
        return PurePosixPath("references") / PurePosixPath(path.relative_to(plugin_root).as_posix())
    if path.is_relative_to(repo_data):
        return PurePosixPath("references/data") / PurePosixPath(path.relative_to(repo_data).as_posix())
    raise ResourceResolutionError(f"Resource {path} is outside the owned plugin/data trees")


def derive_bundle(skill: SkillRecord) -> Bundle:
    """Derive the recursive local resource closure of one canonical skill."""
    pending = [skill.path]
    seen_documents: set[Path] = set()
    references: list[ResourceReference] = []
    support: set[Path] = set()
    while pending:
        document = pending.pop()
        if document in seen_documents:
            continue
        seen_documents.add(document)
        document_references = scan_references(document, skill.plugin)
        references.extend(document_references)
        for reference in document_references:
            if reference.classification == "unresolved_local":
                raise ResourceResolutionError(f"{document}: unresolved local resource {reference.raw!r}")
            resolved = reference.resolved_path
            if resolved is None:
                continue
            support.add(resolved)
            if resolved.suffix == ".md" and resolved.is_file() and not _is_dataset(resolved, skill.plugin):
                pending.append(resolved)
            if resolved.is_dir() and not _is_dataset(resolved, skill.plugin):
                pending.extend(path for path in resolved.rglob("*.md"))
    data_paths = sorted(path for path in support if _is_plugin_data(path, skill.plugin))
    hashes = {
        _reference_destination(file_path, skill.plugin).as_posix(): sha256_file(file_path)
        for data_path in data_paths for file_path in _iter_files(data_path)
    }
    return Bundle(skill.path, skill.plugin, tuple(references), tuple(sorted(support)), bool(data_paths), hashes)


def derive_resources(skill: SkillRecord) -> Bundle:
    """Public plan-facing name for the derived standalone resource closure."""
    return derive_bundle(skill)


def _destination_for_reference(reference: ResourceReference, plugin: PluginMeta) -> str | None:
    if reference.resolved_path is None:
        return None
    target = reference.resolved_path
    if target.is_file():
        return _reference_destination(target, plugin).as_posix()
    return _reference_destination(target, plugin).as_posix() + "/"


def _data_note(plugin: PluginMeta, source: Path) -> str:
    if _is_research_data(source, plugin):
        location = "data/ (repository research bundle)"
    else:
        location = f"plugins/{plugin.name}/data/"
    return f"Dataset omitted from this standalone install; use --with-data where available (source: {location})"


def installed_form(skill: SkillRecord, with_data: bool = False) -> InstalledForm:
    """Produce the exact destination files for a standalone install, without writes."""
    bundle = derive_bundle(skill)
    files: dict[PurePosixPath, bytes] = {}
    plugin_data_paths = {path for path in bundle.support_paths if _is_plugin_data(path, skill.plugin)}
    research_data_paths = {path for path in bundle.support_paths if _is_research_data(path, skill.plugin)}

    # Copy each cited support tree once. Markdown support documents receive the
    # same reference rewrite as the entrypoint, preserving their own closure.
    source_documents = [skill.path]
    for path in bundle.support_paths:
        if path.is_file() and not _is_dataset(path, skill.plugin):
            source_documents.append(path)
    document_text: dict[Path, str] = {}
    for source in source_documents:
        text = source.read_text(encoding="utf-8")
        references = scan_references(source, skill.plugin)
        for reference in references:
            if _is_dataset(reference.resolved_path, skill.plugin) if reference.resolved_path else False:
                replacement = _destination_for_reference(reference, skill.plugin) if with_data and _is_plugin_data(reference.resolved_path, skill.plugin) else _data_note(skill.plugin, reference.resolved_path)
            else:
                replacement = _destination_for_reference(reference, skill.plugin)
            if replacement:
                text = text.replace(reference.raw, replacement)
        document_text[source] = text

    files[PurePosixPath("SKILL.md")] = document_text[skill.path].encode("utf-8")
    for source, text in document_text.items():
        if source == skill.path:
            continue
        files[_reference_destination(source, skill.plugin)] = text.encode("utf-8")
    for source in bundle.support_paths:
        if source in research_data_paths or (source in plugin_data_paths and not with_data):
            continue
        for file_path in _iter_files(source):
            destination = _reference_destination(file_path, skill.plugin)
            if destination not in files:
                files[destination] = file_path.read_bytes()
    form = InstalledForm(skill, files, document_text[skill.path], bundle, with_data)
    verify_installed_form(form)
    return form


def verify_installed_form(form: InstalledForm) -> None:
    """Assert that rewritten local references resolve inside the materialized tree."""
    for destination, content in form.files.items():
        if destination.suffix != ".md":
            continue
        for raw in _raw_references(content.decode("utf-8")):
            if not raw.startswith("references/"):
                continue
            candidate = PurePosixPath(raw.rstrip("/"))
            if candidate not in form.files and not any(path.is_relative_to(candidate) for path in form.files):
                raise ResourceResolutionError(f"Installed {destination} references absent resource {raw}")


def materialize_skill(skill: SkillRecord, destination: Path, with_data: bool = False) -> InstalledForm:
    """Write one already-derived standalone tree. The installer controls atomicity."""
    form = installed_form(skill, with_data=with_data)
    for relative, content in form.files.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return form
