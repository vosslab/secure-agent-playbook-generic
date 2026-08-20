"""Repository-shaped discovery helpers used by generators and diagnostics."""

from __future__ import annotations

from pathlib import Path

from plugin_metadata import AgentRecord, PluginMeta, RepositoryInventory, SkillRecord, discover_repository


REPO_ROOT = Path(__file__).resolve().parent.parent


def inventory(repo_root: Path = REPO_ROOT) -> RepositoryInventory:
    return discover_repository(repo_root)


def discover_skills(repo_root: Path = REPO_ROOT) -> tuple[SkillRecord, ...]:
    return inventory(repo_root).skills


def discover_agents(repo_root: Path = REPO_ROOT) -> tuple[AgentRecord, ...]:
    return inventory(repo_root).agents


def discover_plugins(repo_root: Path = REPO_ROOT) -> tuple[PluginMeta, ...]:
    return inventory(repo_root).plugins


def render_discovery_summary(repo_root: Path = REPO_ROOT) -> list[str]:
    found = inventory(repo_root)
    return [
        "Security playbook inventory:",
        f"  Plugins: {len(found.plugins)}",
        f"  Skills: {len(found.skills)}",
        f"  Agents: {len(found.agents)}",
    ]
