"""Read the canonical plugin skills and agents."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Plugin:
    name: str
    path: Path


@dataclass(frozen=True)
class Skill:
    name: str
    path: Path
    plugin: Plugin


@dataclass(frozen=True)
class Agent:
    name: str
    description: str
    path: Path
    plugin: Plugin
    frontmatter: dict[str, Any]
    body: str


@dataclass(frozen=True)
class Inventory:
    skills: tuple[Skill, ...]
    agents: tuple[Agent, ...]


def _frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path} must begin with YAML frontmatter")
    header, body = text[4:].split("\n---\n", 1)
    metadata = yaml.safe_load(header) or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"{path} frontmatter must be a mapping")
    return metadata, body


def _required(metadata: dict[str, Any], field: str, path: Path) -> str:
    value = metadata[field]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} requires non-empty {field!r}")
    return value.strip()


def discover_repository(repo_root: Path) -> Inventory:
    """Discover canonical plugin skills and agents in filename order."""
    skills: list[Skill] = []
    agents: list[Agent] = []
    for plugin_path in sorted((repo_root / "plugins").iterdir()):
        if not plugin_path.is_dir():
            continue
        plugin = Plugin(plugin_path.name, plugin_path)
        for path in sorted((plugin_path / "skills").glob("*/SKILL.md")):
            metadata, _ = _frontmatter(path)
            skills.append(Skill(_required(metadata, "name", path), path, plugin))
        for path in sorted((plugin_path / "agents").glob("*.md")):
            metadata, body = _frontmatter(path)
            agents.append(Agent(
                _required(metadata, "name", path),
                _required(metadata, "description", path),
                path,
                plugin,
                metadata,
                body,
            ))
    skill_names = [skill.name for skill in skills]
    agent_names = [agent.name for agent in agents]
    if len(skill_names) != len(set(skill_names)):
        raise ValueError("Skill names must be unique")
    if len(agent_names) != len(set(agent_names)):
        raise ValueError("Agent names must be unique")
    return Inventory(tuple(skills), tuple(agents))
