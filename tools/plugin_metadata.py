"""Typed inventory of the authored Claude plugin corpus.

The module has one job: read the existing source tree faithfully. Generators
and installers consume these records; none infer identity from paths or carry
an independent list of skills.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

import yaml


class MetadataError(ValueError):
    """Raised when source metadata cannot describe a portable artifact."""


@dataclass(frozen=True)
class FrontmatterDocument:
    metadata: dict[str, Any]
    body: str


@dataclass(frozen=True)
class PluginMeta:
    name: str
    description: str
    version: str
    path: Path
    manifest_path: Path
    manifest: dict[str, Any]

    @property
    def author(self) -> Any:
        return self.manifest.get("author")

    @property
    def homepage(self) -> str | None:
        value = self.manifest.get("homepage")
        return value if isinstance(value, str) else None


PluginRecord = PluginMeta


@dataclass(frozen=True)
class SkillRecord:
    name: str
    description: str
    path: Path
    plugin: PluginMeta
    frontmatter: dict[str, Any]
    body: str

    @property
    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class AgentRecord:
    name: str
    description: str
    path: Path
    plugin: PluginMeta
    frontmatter: dict[str, Any]
    body: str


@dataclass(frozen=True)
class RepositoryInventory:
    root: Path
    plugins: tuple[PluginMeta, ...]
    skills: tuple[SkillRecord, ...]
    agents: tuple[AgentRecord, ...]


def parse_frontmatter(text: str, *, source: str = "document") -> FrontmatterDocument:
    """Parse YAML frontmatter with ``yaml.safe_load`` and retain the body exactly."""
    if not text.startswith("---\n"):
        raise MetadataError(f"{source} must begin with YAML frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise MetadataError(f"{source} has unterminated YAML frontmatter")
    closing_newline = text.find("\n", end + 4)
    if closing_newline < 0:
        raise MetadataError(f"{source} has an incomplete frontmatter closing marker")
    try:
        parsed = yaml.safe_load(text[4:end]) or {}
    except yaml.YAMLError as exc:
        raise MetadataError(f"{source} has invalid YAML frontmatter: {exc}") from exc
    if not isinstance(parsed, dict) or any(not isinstance(key, str) for key in parsed):
        raise MetadataError(f"{source} frontmatter must be a string-keyed mapping")
    return FrontmatterDocument(dict(parsed), text[closing_newline + 1 :])


def _required_string(mapping: dict[str, Any], field: str, source: Path) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise MetadataError(f"{source} requires non-empty {field!r}")
    return value.strip()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MetadataError(f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MetadataError(f"{path} must contain a JSON object")
    return value


def load_plugin_meta(plugin_path: Path) -> PluginMeta:
    """Load one plugin from its authoritative Claude manifest."""
    manifest_path = plugin_path / ".claude-plugin" / "plugin.json"
    manifest = _read_json(manifest_path)
    return PluginMeta(
        name=_required_string(manifest, "name", manifest_path),
        description=_required_string(manifest, "description", manifest_path),
        version=_required_string(manifest, "version", manifest_path),
        path=plugin_path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def discover_repository(repo_root: Path) -> RepositoryInventory:
    """Discover only canonical plugin skills and agents in deterministic order."""
    root = repo_root.resolve()
    plugins_root = root / "plugins"
    if not plugins_root.is_dir():
        raise MetadataError(f"Missing plugin source directory: {plugins_root}")
    plugins: list[PluginMeta] = []
    skills: list[SkillRecord] = []
    agents: list[AgentRecord] = []
    for plugin_path in sorted(path for path in plugins_root.iterdir() if path.is_dir()):
        manifest_path = plugin_path / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            continue
        plugin = load_plugin_meta(plugin_path)
        plugins.append(plugin)
        for path in sorted((plugin.path / "skills").glob("*/SKILL.md")):
            document = parse_frontmatter(path.read_text(encoding="utf-8"), source=str(path))
            skills.append(SkillRecord(
                name=_required_string(document.metadata, "name", path),
                description=_required_string(document.metadata, "description", path),
                path=path,
                plugin=plugin,
                frontmatter=document.metadata,
                body=document.body,
            ))
        for path in sorted((plugin.path / "agents").glob("*.md")):
            document = parse_frontmatter(path.read_text(encoding="utf-8"), source=str(path))
            agents.append(AgentRecord(
                name=_required_string(document.metadata, "name", path),
                description=_required_string(document.metadata, "description", path),
                path=path,
                plugin=plugin,
                frontmatter=document.metadata,
                body=document.body,
            ))
    _unique((skill.name for skill in skills), "skill")
    _unique((agent.name for agent in agents), "agent")
    return RepositoryInventory(root, tuple(plugins), tuple(skills), tuple(agents))


def _unique(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        raise MetadataError(f"Duplicate {label} names: {', '.join(sorted(duplicates))}")
