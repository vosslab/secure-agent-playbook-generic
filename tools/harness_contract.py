"""Declarative filesystem contracts for the supported agent harnesses.

Claude and Codex are the primary distribution targets. OpenCode uses the same
contract mechanism as a compatibility surface, so its paths stay inspectable
and testable without making a local OpenCode binary a release prerequisite.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


Scope = Literal["user", "project"]
ArtifactKind = Literal["skills", "agents", "plugin"]


@dataclass(frozen=True)
class HarnessSpec:
    id: str
    display_name: str
    user_skill_root: Path
    project_skill_root: Path
    user_agent_root: Path | None
    project_agent_root: Path | None
    agent_format: str | None
    instructions_file: str
    plugin_manifest: Path | None
    user_skill_compatibility_roots: tuple[Path, ...] = ()
    project_skill_compatibility_roots: tuple[Path, ...] = ()

    def destination(self, scope: Scope, kind: ArtifactKind, *, home: Path, project_root: Path) -> Path:
        root = home if scope == "user" else project_root
        if kind == "skills":
            relative = self.user_skill_root if scope == "user" else self.project_skill_root
        elif kind == "agents":
            relative = self.user_agent_root if scope == "user" else self.project_agent_root
        elif kind == "plugin":
            relative = self.plugin_manifest.parent if self.plugin_manifest else None
        else:
            raise ValueError(f"Unsupported artifact kind: {kind}")
        if relative is None:
            raise ValueError(f"{self.display_name} has no {kind} installation target")
        return root / relative

    def discovery_roots(self, scope: Scope, *, home: Path, project_root: Path) -> tuple[Path, ...]:
        root = home if scope == "user" else project_root
        primary = self.user_skill_root if scope == "user" else self.project_skill_root
        extras = self.user_skill_compatibility_roots if scope == "user" else self.project_skill_compatibility_roots
        return tuple(root / path for path in (primary, *extras))


CLAUDE = HarnessSpec(
    id="claude",
    display_name="Claude Code",
    user_skill_root=Path(".claude/skills"),
    project_skill_root=Path(".claude/skills"),
    user_agent_root=None,
    project_agent_root=None,
    agent_format=None,
    instructions_file="CLAUDE.md",
    plugin_manifest=Path(".claude-plugin/plugin.json"),
)
CODEX = HarnessSpec(
    id="codex",
    display_name="Codex CLI",
    user_skill_root=Path(".agents/skills"),
    project_skill_root=Path(".agents/skills"),
    user_agent_root=Path(".codex/agents"),
    project_agent_root=Path(".codex/agents"),
    agent_format="toml",
    instructions_file="AGENTS.md",
    plugin_manifest=Path(".codex-plugin/plugin.json"),
)
OPENCODE = HarnessSpec(
    id="opencode",
    display_name="OpenCode (compatibility)",
    user_skill_root=Path(".config/opencode/skills"),
    project_skill_root=Path(".opencode/skills"),
    user_agent_root=Path(".config/opencode/agent"),
    project_agent_root=Path(".opencode/agent"),
    agent_format="md",
    instructions_file="AGENTS.md",
    plugin_manifest=None,
    user_skill_compatibility_roots=(Path(".claude/skills"), Path(".agents/skills")),
    project_skill_compatibility_roots=(Path(".claude/skills"), Path(".agents/skills")),
)

HARNESS_SPECS: tuple[HarnessSpec, ...] = (CLAUDE, CODEX, OPENCODE)
HARNESS_BY_ID = {spec.id: spec for spec in HARNESS_SPECS}


def render_support_table() -> str:
    """Render the README support table directly from this contract."""
    rows = [
        "| Harness | Support | User skills | Project skills | Agents |",
        "| --- | --- | --- | --- | --- |",
    ]
    for spec, support in ((CLAUDE, "Primary"), (CODEX, "Primary"), (OPENCODE, "Best-effort compatibility")):
        user_agent = str(spec.user_agent_root) if spec.user_agent_root else "Marketplace"
        rows.append(f"| {spec.display_name} | {support} | `~/{spec.user_skill_root}` | `{spec.project_skill_root}` | `{user_agent}` |")
    return "\n".join(rows)


def get_harness(target: str | HarnessSpec) -> HarnessSpec:
    if isinstance(target, HarnessSpec):
        return target
    try:
        return HARNESS_BY_ID[target]
    except KeyError as exc:
        raise ValueError(f"Unknown harness {target!r}; choose one of {', '.join(HARNESS_BY_ID)}") from exc


def resolve_destination(
    target: str | HarnessSpec,
    scope: Scope,
    *,
    home: Path,
    project_root: Path,
    kind: ArtifactKind = "skills",
) -> Path:
    """Compatibility wrapper used by installer and fixture code."""
    return get_harness(target).destination(scope, kind, home=home, project_root=project_root)


def simulate_skill_discovery(
    target: str | HarnessSpec,
    *,
    cwd: Path,
    home: Path,
    repo_root: Path | None = None,
) -> tuple[Path, ...]:
    """Model documented ancestor then user-scope skill discovery over a fixture tree."""
    spec = get_harness(target)
    current = cwd.resolve()
    found: list[Path] = []
    while True:
        for relative in (spec.project_skill_root, *spec.project_skill_compatibility_roots):
            candidate = current / relative
            if candidate.is_dir() and candidate not in found:
                found.append(candidate)
        if repo_root is not None and current == repo_root.resolve():
            break
        if current.parent == current:
            break
        current = current.parent
    for relative in (spec.user_skill_root, *spec.user_skill_compatibility_roots):
        candidate = home.resolve() / relative
        if candidate.is_dir() and candidate not in found:
            found.append(candidate)
    return tuple(found)


def simulate_codex_skill_discovery(*, cwd: Path, repo_root: Path, home: Path) -> list[Path]:
    """Legacy-named fixture helper restricted to the requested repository walk."""
    roots = simulate_skill_discovery(CODEX, cwd=cwd, home=home, repo_root=repo_root)
    return list(roots)
