"""Render canonical Claude agents for Codex and OpenCode surfaces."""

from __future__ import annotations

import json
import yaml

from plugin_metadata import AgentRecord


def namespaced_agent_name(agent: AgentRecord) -> str:
    """Keep independently installable plugin agents collision-resistant."""
    return f"{agent.plugin.name}--{agent.name}"


def agent_filename(agent: AgentRecord, suffix: str = ".toml") -> str:
    return f"{namespaced_agent_name(agent)}{suffix}"


def _instructions(agent: AgentRecord) -> str:
    skills = agent.frontmatter.get("skills", "")
    if isinstance(skills, str):
        skill_names = [item.strip() for item in skills.split(",") if item.strip()]
    elif isinstance(skills, list):
        skill_names = [str(item) for item in skills]
    else:
        skill_names = []
    skill_line = "Use the installed skills most relevant to the task."
    if skill_names:
        skill_line = f"Use these installed skills when relevant: {', '.join(skill_names)}."
    return f"{skill_line}\n\n{agent.body.lstrip()}"


def _toml_multiline(value: str) -> str:
    """Escape a value for a TOML multiline basic string without changing it."""
    escaped = value.replace("\\", "\\\\").replace('"""', '\\"""')
    return f'"""\\\n{escaped}"""'


def to_codex_toml(agent: AgentRecord) -> str:
    """Emit a TOML agent with safe JSON-string quoting for every source value."""
    return (
        f"name = {json.dumps(namespaced_agent_name(agent), ensure_ascii=False)}\n"
        f"description = {json.dumps(agent.description, ensure_ascii=False)}\n"
        f"developer_instructions = {_toml_multiline(_instructions(agent))}\n"
        'sandbox_mode = "read-only"\n'
    )


def _opencode_permissions(agent: AgentRecord) -> dict[str, str]:
    tools = agent.frontmatter.get("tools", "")
    source = tools if isinstance(tools, list) else str(tools).split(",")
    mapped = {"read": "read", "grep": "grep", "glob": "glob", "bash": "bash", "webfetch": "webfetch", "agent": "agent"}
    permissions: dict[str, str] = {}
    for tool in source:
        key = mapped.get(str(tool).strip().lower())
        if key:
            permissions[key] = "allow"
    return permissions


def to_opencode_md(agent: AgentRecord) -> str:
    """Emit an OpenCode subagent that preserves its authorized tool vocabulary."""
    frontmatter = {
        "generated_by": "tools/build_plugin_manifest.py",
        "description": agent.description,
        "mode": "subagent",
        "permission": _opencode_permissions(agent),
    }
    header = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{header}\n---\n\n{_instructions(agent)}"
