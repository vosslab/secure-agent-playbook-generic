#!/usr/bin/env python3
"""Install the security playbook through a fresh guided interview."""

import argparse
from pathlib import Path, PurePosixPath
import shutil
from typing import Any, Iterable, Sequence

from install_lib.convert_agents import agent_filename, to_codex_toml, to_opencode_md
from install_lib.plugin_metadata import discover_repository
from install_lib.resource_resolver import installed_files


REPO_ROOT = Path(__file__).resolve().parent
DESTINATIONS = {
    "claude": {
        "user": (Path(".claude/skills"), Path(".claude/agents")),
        "project": (Path(".claude/skills"), Path(".claude/agents")),
    },
    "codex": {
        "user": (Path(".agents/skills"), Path(".codex/agents")),
        "project": (Path(".agents/skills"), Path(".codex/agents")),
    },
    "opencode": {
        "user": (Path(".config/opencode/skills"), Path(".config/opencode/agents")),
        "project": (Path(".opencode/skills"), Path(".opencode/agents")),
    },
}


def detect_harnesses(home: Path) -> dict[str, bool]:
    """Report local harness configuration roots; absence remains installable."""
    return {
        "claude": (home / ".claude").exists(),
        "codex": (home / ".codex").exists() or (home / ".agents").exists(),
        "opencode": (home / ".config/opencode").exists(),
    }


def _choice(prompt: str, choices: Iterable[str], default: str) -> str:
    allowed = tuple(choices)
    while True:
        answer = input(f"{prompt} [{default}]: ").strip() or default
        if answer in allowed:
            return answer
        print(f"Choose one of: {', '.join(allowed)}")


def interview(home: Path) -> tuple[tuple[str, ...], str]:
    """Collect a fresh installation selection."""
    detected = detect_harnesses(home)
    print("Detected harness roots:", ", ".join(name for name, present in detected.items() if present) or "none")
    # Ask only about installation topology. Required content such as cited
    # datasets is automatic and must never become another question or flag.
    selected = input("Targets (comma-separated claude,codex,opencode) [claude,codex]: ").strip() or "claude,codex"
    targets = tuple(dict.fromkeys(item.strip() for item in selected.split(",") if item.strip()))
    if not targets or any(target not in DESTINATIONS for target in targets):
        raise ValueError("Targets must be chosen from claude,codex,opencode")
    scope = _choice("Scope (user/project)", ("user", "project"), "user")
    if _choice("Install now (yes/no)", ("yes", "no"), "yes") != "yes":
        raise RuntimeError("Installation cancelled")
    return targets, scope


def _agent_path(agent: Any, target: str) -> PurePosixPath:
    if target == "claude":
        return PurePosixPath(agent.path.name)
    suffix = ".toml" if target == "codex" else ".md"
    return PurePosixPath(agent_filename(agent, suffix))


def _agent_content(agent: Any, target: str) -> tuple[PurePosixPath, bytes]:
    # Canonical agents are authored for Claude already. Preserve them exactly;
    # only harnesses with a different format need conversion here.
    if target == "claude":
        return _agent_path(agent, target), agent.path.read_bytes()
    if target == "codex":
        return _agent_path(agent, target), to_codex_toml(agent).encode("utf-8")
    return _agent_path(agent, target), to_opencode_md(agent).encode("utf-8")


def _desired_skills(skills: Iterable[Any]) -> tuple[dict[PurePosixPath, bytes], ...]:
    desired: list[dict[PurePosixPath, bytes]] = []
    for skill in skills:
        # A usable skill is the entrypoint plus its complete local closure,
        # including every cited dataset. There is deliberately no thin mode.
        files = installed_files(skill)
        desired.append({
            PurePosixPath(skill.name) / relative: content for relative, content in files.items()
        })
    return tuple(desired)


def _desired_agents(agents: Iterable[Any], target: str) -> tuple[dict[PurePosixPath, bytes], ...]:
    desired: list[dict[PurePosixPath, bytes]] = []
    for agent in agents:
        relative, content = _agent_content(agent, target)
        desired.append({relative: content})
    return tuple(desired)


def _destination(target: str, scope: str, component: str, *, home: Path, project_root: Path) -> Path:
    base = home if scope == "user" else project_root
    index = 0 if component == "skills" else 1
    return base / DESTINATIONS[target][scope][index]


def _remove_path(path: Path) -> None:
    """Remove one managed path without following a symlink."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _write_component(root: Path, files: dict[PurePosixPath, bytes]) -> None:
    """Replace only this component's complete top-level paths."""
    root.mkdir(parents=True, exist_ok=True)
    top_levels = {path.parts[0] for path in files}
    for top_level in top_levels:
        _remove_path(root / top_level)
    for relative, content in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def install(
    targets: tuple[str, ...],
    scope: str,
    *,
    repo_root: Path = REPO_ROOT,
    home: Path,
    project_root: Path,
) -> dict[str, int]:
    report: dict[str, int] = {}
    found = discover_repository(repo_root)
    skills = _desired_skills(found.skills)
    for target in targets:
        skill_root = _destination(target, scope, "skills", home=home, project_root=project_root)
        for files in skills:
            _write_component(skill_root, files)
        report[f"{target}:skills"] = len(skills)
        data_count = sum("references/data" in path.as_posix() for files in skills for path in files)
        print(f"{target}: cited dataset resource files: {data_count}")

        agent_root = _destination(target, scope, "agents", home=home, project_root=project_root)
        agents = _desired_agents(found.agents, target)
        for files in agents:
            _write_component(agent_root, files)
        report[f"{target}:agents"] = len(agents)
    return report


def uninstall(*, repo_root: Path, home: Path, project_root: Path) -> None:
    """Remove known skills and agents wherever their key files are installed."""
    removed: set[Path] = set()
    scopes = ("user",) if project_root == repo_root else ("user", "project")
    found = discover_repository(repo_root)
    # ASVS 2.3.1: derive every removal from a canonical key file and known root.
    for target in DESTINATIONS:
        for scope in scopes:
            skill_root = _destination(target, scope, "skills", home=home, project_root=project_root)
            skill_count = 0
            for skill in found.skills:
                installed_path = skill_root / skill.name
                if (installed_path / "SKILL.md").is_file() and installed_path not in removed:
                    _remove_path(installed_path)
                    removed.add(installed_path)
                    skill_count += 1
            if skill_count:
                print(f"{target}:skills: removed {skill_count} from {skill_root}")

            agent_root = _destination(target, scope, "agents", home=home, project_root=project_root)
            agent_count = 0
            for agent in found.agents:
                installed_path = agent_root / _agent_path(agent, target)
                if installed_path.is_file() and installed_path not in removed:
                    _remove_path(installed_path)
                    removed.add(installed_path)
                    agent_count += 1
            if agent_count:
                print(f"{target}:agents: removed {agent_count} from {agent_root}")
    print(f"Uninstalled {len(removed)} skill and agent paths.")


def _report(report: dict[str, int]) -> None:
    for location, count in report.items():
        print(f"{location}: installed {count}")


def main(
    argv: Sequence[str] | None = None,
    *,
    repo_root: Path | None = None,
    home: Path | None = None,
    project_root: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # Public argparse policy is intentionally strict: expose only switches a
    # user plausibly changes between runs. See docs/FORK_CONTRACT.md.
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)

    resolved_home = (home or Path.home()).resolve()
    resolved_repo = (repo_root or REPO_ROOT).resolve()
    resolved_project = (project_root or Path.cwd()).resolve()
    if args.uninstall:
        uninstall(repo_root=resolved_repo, home=resolved_home, project_root=resolved_project)
        return 0

    # ASVS 2.3.1: collect this operation's topology in sequence immediately
    # before acting; no prior response is cached or silently replayed.
    targets, scope = interview(resolved_home)
    report = install(
        targets,
        scope,
        repo_root=resolved_repo,
        home=resolved_home,
        project_root=resolved_project,
    )
    _report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
