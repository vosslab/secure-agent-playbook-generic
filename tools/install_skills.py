"""Install the security playbook through a saved, repeatable harness profile."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any, Iterable, Literal

from build_plugin_manifest import codex_manifest, marketplace, opencode_config
from convert_agents import agent_filename, to_codex_toml, to_opencode_md
from harness_contract import HARNESS_BY_ID, HarnessSpec, get_harness, resolve_destination
from resource_resolver import InstalledForm, installed_form
from skill_discovery import inventory


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
MANIFEST_NAME = ".agent-security-playbook.json"
PROFILE_RELATIVE = Path(".config/agent-security-playbook/profile.json")
State = Literal["current", "outdated", "modified", "orphaned", "missing"]


class ManagedContentModified(RuntimeError):
    """An operation needs permission to replace locally changed managed files."""


@dataclass(frozen=True)
class InstallProfile:
    targets: tuple[str, ...]
    scope: str
    components: tuple[str, ...]
    with_data: bool
    overwrite: str
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class ComponentStatus:
    component: str
    state: State
    harnesses: tuple[str, ...]
    detail: str = ""


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Invalid managed relative path: {value!r}")
    return path


def _read_json(path: Path, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return dict(fallback or {})
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return parsed


def profile_path(home: Path, name: str = "default") -> Path:
    if name == "default":
        return home / PROFILE_RELATIVE
    return home / ".config/agent-security-playbook/profiles" / f"{name}.json"


def load_profile(home: Path, name: str = "default") -> InstallProfile | None:
    path = profile_path(home, name)
    if not path.is_file():
        return None
    data = _read_json(path)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported profile schema in {path}")
    return InstallProfile(
        tuple(data["targets"]), data["scope"], tuple(data["components"]),
        bool(data.get("with_data")), str(data.get("overwrite", "ask")), SCHEMA_VERSION,
    )


def save_profile(home: Path, profile: InstallProfile, name: str = "default") -> Path:
    path = profile_path(home, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(profile), indent=2) + "\n", encoding="utf-8")
    return path


def detect_harnesses(home: Path) -> dict[str, bool]:
    """Report local harness configuration roots; absence remains installable."""
    checks = {
        "claude": home / ".claude",
        "codex": home / ".codex",
        "agents": home / ".agents",
        "opencode": home / ".config/opencode",
    }
    return {name: path.exists() for name, path in checks.items()}


def _choice(prompt: str, choices: Iterable[str], default: str) -> str:
    allowed = tuple(choices)
    while True:
        answer = input(f"{prompt} [{default}]: ").strip() or default
        if answer in allowed:
            return answer
        print(f"Choose one of: {', '.join(allowed)}")


def interview(home: Path) -> InstallProfile:
    """Collect an explicit first-run profile; saved runs use --yes thereafter."""
    detected = detect_harnesses(home)
    print("Detected harness roots:", ", ".join(name for name, present in detected.items() if present) or "none")
    selected = input("Targets (comma-separated claude,codex,opencode) [claude,codex]: ").strip() or "claude,codex"
    targets = tuple(dict.fromkeys(item.strip() for item in selected.split(",") if item.strip()))
    if not targets or any(target not in HARNESS_BY_ID for target in targets):
        raise ValueError("Targets must be chosen from claude,codex,opencode")
    scope = _choice("Install scope (user/project)", ("user", "project"), "user")
    selected_components = input("Components (comma-separated skills,agents) [skills,agents]: ").strip() or "skills,agents"
    components = tuple(dict.fromkeys(item.strip() for item in selected_components.split(",") if item.strip()))
    if not components or any(component not in {"skills", "agents"} for component in components):
        raise ValueError("Components must be skills and/or agents")
    data_choice = _choice("Include cited datasets (yes/no)", ("yes", "no"), "no")
    overwrite = _choice("Replace locally modified managed content (ask/force)", ("ask", "force"), "ask")
    profile = InstallProfile(targets, scope, components, data_choice == "yes", overwrite)
    print("Planned profile:", json.dumps(asdict(profile), sort_keys=True))
    if _choice("Save and install now (yes/no)", ("yes", "no"), "yes") != "yes":
        raise RuntimeError("Installation cancelled")
    return profile


def _component_key(kind: str, name: str) -> str:
    return f"{kind}:{name}"


def _agent_content(agent: Any, harness: HarnessSpec) -> tuple[PurePosixPath, bytes] | None:
    if harness.agent_format == "toml":
        return PurePosixPath(agent_filename(agent)), to_codex_toml(agent).encode("utf-8")
    if harness.agent_format == "md" and harness.id == "opencode":
        return PurePosixPath(agent_filename(agent, ".md")), to_opencode_md(agent).encode("utf-8")
    return None


def _desired_components(repo_root: Path, harness: HarnessSpec, components: tuple[str, ...], with_data: bool) -> dict[str, dict[PurePosixPath, bytes]]:
    found = inventory(repo_root)
    desired: dict[str, dict[PurePosixPath, bytes]] = {}
    if "skills" in components:
        for skill in found.skills:
            form: InstalledForm = installed_form(skill, with_data=with_data)
            desired[_component_key("skill", skill.name)] = {
                PurePosixPath(skill.name) / relative: content for relative, content in form.files.items()
            }
    if "agents" in components:
        for agent in found.agents:
            result = _agent_content(agent, harness)
            if result is not None:
                relative, content = result
                desired[_component_key("agent", agent_filename(agent, ""))] = {relative: content}
    return desired


def _package_root(scope: str, *, home: Path, project_root: Path) -> Path:
    """Return the installer-owned location for complete Codex plugin bundles."""
    return (home / ".config/agent-security-playbook/packages") if scope == "user" else (project_root / ".agent-security-playbook/packages")


def _codex_package_components(repo_root: Path) -> dict[str, dict[PurePosixPath, bytes]]:
    """Copy canonical plugins, then add Codex manifests inside the package copy."""
    found = inventory(repo_root)
    package_files: dict[PurePosixPath, bytes] = {}
    for plugin in found.plugins:
        for source in sorted(plugin.path.rglob("*")):
            if not source.is_file() or ".codex-plugin" in source.parts:
                continue
            relative = PurePosixPath("plugins") / plugin.path.name / PurePosixPath(source.relative_to(plugin.path).as_posix())
            package_files[relative] = source.read_bytes()
        package_files[PurePosixPath("plugins") / plugin.path.name / ".codex-plugin/plugin.json"] = (
            json.dumps(codex_manifest(plugin), indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        )
    package_files[PurePosixPath("marketplace.json")] = (json.dumps(marketplace(found), indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    package_files[PurePosixPath("AGENTS.md")] = (
        "<!-- Generated by tools/install_skills.py from canonical CLAUDE.md. -->\n\n"
        + (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    ).encode("utf-8")
    return {_component_key("package", "codex"): package_files}


def _opencode_config_component(config_root: Path) -> dict[str, dict[PurePosixPath, bytes]]:
    """Generate an OpenCode config in its selected target, preserving user keys."""
    existing = _read_json(config_root / "opencode.json") if (config_root / "opencode.json").is_file() else {}
    content = json.dumps(opencode_config(existing), indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    return {_component_key("config", "opencode"): {PurePosixPath("opencode.json"): content}}


def _manifest(root: Path) -> dict[str, Any]:
    data = _read_json(root / MANIFEST_NAME, {"schema_version": SCHEMA_VERSION, "components": {}})
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported install manifest: {root / MANIFEST_NAME}")
    components = data.get("components", {})
    if not isinstance(components, dict):
        raise ValueError(f"Invalid components in {root / MANIFEST_NAME}")
    for record in components.values():
        if not isinstance(record, dict) or not isinstance(record.get("paths", {}), dict):
            raise ValueError(f"Invalid component record in {root / MANIFEST_NAME}")
        for path in record["paths"]:
            _safe_relative(path)
    data["components"] = components
    return data


def _state_for(root: Path, record: dict[str, Any], desired: dict[PurePosixPath, bytes] | None) -> State:
    recorded = {PurePosixPath(path): digest for path, digest in record.get("paths", {}).items()}
    actual: dict[PurePosixPath, str | None] = {}
    for relative in recorded:
        target = root / relative
        actual[relative] = sha256_bytes(target.read_bytes()) if target.is_file() else None
    if any(value is None for value in actual.values()):
        return "missing"
    if any(actual[path] != recorded[path] for path in recorded):
        return "modified"
    if desired is None:
        return "orphaned"
    expected = {path: sha256_bytes(content) for path, content in desired.items()}
    return "current" if expected == recorded else "outdated"


def status_target(
    root: Path,
    desired: dict[str, dict[PurePosixPath, bytes]] | None = None,
) -> tuple[ComponentStatus, ...]:
    """Classify managed components without writes, including every lifecycle state."""
    manifest = _manifest(root)
    records = manifest["components"]
    result: list[ComponentStatus] = []
    for key in sorted(set(records) | set(desired or {})):
        record = records.get(key)
        if record is None:
            result.append(ComponentStatus(key, "missing", (), "not yet managed"))
            continue
        state = _state_for(root, record, (desired or {}).get(key))
        result.append(ComponentStatus(key, state, tuple(record.get("harnesses", ()))) )
    return tuple(result)


def _stage_root(root: Path) -> Path:
    root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".agent-security-playbook-stage-", dir=root.parent))
    staged_root = stage / "root"
    if root.exists():
        shutil.copytree(root, staged_root)
    else:
        staged_root.mkdir()
    return stage


def _write_component(staged_root: Path, files: dict[PurePosixPath, bytes]) -> dict[str, str]:
    # Every component owns one top-level skill directory or one agent file.
    top_levels = {path.parts[0] for path in files}
    for top_level in top_levels:
        target = staged_root / top_level
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    hashes: dict[str, str] = {}
    for relative, content in files.items():
        target = staged_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        hashes[relative.as_posix()] = sha256_bytes(content)
    return hashes


def _commit_stage(root: Path, stage: Path) -> None:
    staged_root = stage / "root"
    backup = stage / "previous"
    if root.exists():
        os.replace(root, backup)
    try:
        os.replace(staged_root, root)
    except Exception:
        if backup.exists():
            os.replace(backup, root)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _register_consumer(root: Path, harness_id: str) -> None:
    """Record a harness that reads an already-materialized shared skill tree."""
    manifest = _manifest(root)
    if not manifest["components"]:
        return
    if all(harness_id in record.get("harnesses", ()) for record in manifest["components"].values()):
        return
    stage = _stage_root(root)
    staged_manifest = _manifest(stage / "root")
    for record in staged_manifest["components"].values():
        record["harnesses"] = sorted(set(record.get("harnesses", ())) | {harness_id})
    (stage / "root" / MANIFEST_NAME).write_text(json.dumps(staged_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _commit_stage(root, stage)


def _install_root(
    root: Path,
    desired: dict[str, dict[PurePosixPath, bytes]],
    harness: HarnessSpec,
    *,
    force: bool,
    dry_run: bool,
    repo_version: str,
    skip_modified: bool = False,
    prune: bool = False,
) -> tuple[ComponentStatus, ...]:
    manifest = _manifest(root)
    statuses = status_target(root, desired)
    blocked = [item.component for item in statuses if item.state == "modified" and item.component in desired]
    if blocked and not force and not skip_modified:
        raise ManagedContentModified("Locally modified managed content: " + ", ".join(blocked))
    actionable = [
        item for item in statuses
        if item.component in desired and item.state != "current" and not (skip_modified and item.state == "modified")
    ]
    orphans = [item.component for item in statuses if item.state == "orphaned"] if prune else []
    if dry_run:
        for key in sorted(desired):
            before = (root / next(iter(desired[key]))).read_text(encoding="utf-8", errors="replace") if desired[key] and (root / next(iter(desired[key]))).is_file() else ""
            after = next(iter(desired[key].values())).decode("utf-8", errors="replace")
            if before != after:
                print("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=f"{key}:current", tofile=f"{key}:planned")))
            print(f"{harness.id}: {key} ({len(desired[key])} files)")
        return statuses
    if not actionable and not orphans:
        return statuses
    stage = _stage_root(root)
    staged_root = stage / "root"
    records: dict[str, Any] = dict(manifest["components"])
    for key in orphans:
        for relative in records[key]["paths"]:
            target = staged_root / _safe_relative(relative)
            if target.is_file() or target.is_symlink():
                target.unlink()
        records.pop(key, None)
    for key, files in desired.items():
        state = next((item.state for item in statuses if item.component == key), "missing")
        if state == "current" or (skip_modified and state == "modified" and not force):
            continue
        hashes = _write_component(staged_root, files)
        previous = records.get(key, {})
        consumers = set(previous.get("harnesses", ()))
        consumers.add(harness.id)
        records[key] = {"paths": hashes, "source": "repository", "harnesses": sorted(consumers)}
    next_manifest = {
        "schema_version": SCHEMA_VERSION,
        "playbook_version": repo_version,
        "components": records,
    }
    # The manifest enters the staged root after every component file, then the
    # whole install root switches by rename.
    (staged_root / MANIFEST_NAME).write_text(json.dumps(next_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _commit_stage(root, stage)
    return status_target(root, desired)


def install(
    profile: InstallProfile,
    *,
    repo_root: Path = REPO_ROOT,
    home: Path,
    project_root: Path,
    force: bool = False,
    dry_run: bool = False,
    update: bool = False,
    prune: bool = False,
) -> dict[str, tuple[ComponentStatus, ...]]:
    found = inventory(repo_root)
    version = found.plugins[0].version if found.plugins else "unknown"
    report: dict[str, tuple[ComponentStatus, ...]] = {}
    if "codex" in profile.targets:
        package_root = _package_root(profile.scope, home=home, project_root=project_root)
        package_desired = _codex_package_components(repo_root)
        report["codex:package"] = _install_root(package_root, package_desired, get_harness("codex"), force=force or profile.overwrite == "force", dry_run=dry_run, repo_version=version, skip_modified=update, prune=prune)
    for target in profile.targets:
        harness = get_harness(target)
        if "skills" in profile.components:
            root = resolve_destination(harness, profile.scope, home=home, project_root=project_root, kind="skills")
            desired = _desired_components(repo_root, harness, ("skills",), profile.with_data)
            report[f"{target}:skills"] = _install_root(root, desired, harness, force=force or profile.overwrite == "force", dry_run=dry_run, repo_version=version, skip_modified=update, prune=prune)
            if profile.with_data:
                count = sum(installed_form(skill, with_data=True).data_file_count for skill in found.skills)
                print(f"{target}: planned resource files including datasets: {count}")
        if "agents" in profile.components and harness.user_agent_root is not None:
            root = resolve_destination(harness, profile.scope, home=home, project_root=project_root, kind="agents")
            desired = _desired_components(repo_root, harness, ("agents",), profile.with_data)
            report[f"{target}:agents"] = _install_root(root, desired, harness, force=force or profile.overwrite == "force", dry_run=dry_run, repo_version=version, skip_modified=update, prune=prune)
        if target == "opencode":
            config_root = (home / ".config/opencode") if profile.scope == "user" else project_root
            report["opencode:config"] = _install_root(config_root, _opencode_config_component(config_root), harness, force=force or profile.overwrite == "force", dry_run=dry_run, repo_version=version, skip_modified=update, prune=prune)
    # OpenCode discovers the Codex-shaped user tree as a compatibility source.
    # Record that shared consumer when both primary installations are selected.
    if profile.scope == "user" and "skills" in profile.components and {"codex", "opencode"}.issubset(profile.targets) and not dry_run:
        shared_root = resolve_destination("codex", profile.scope, home=home, project_root=project_root, kind="skills")
        _register_consumer(shared_root, "opencode")
    return report


def status(
    profile: InstallProfile,
    *,
    repo_root: Path,
    home: Path,
    project_root: Path,
) -> dict[str, tuple[ComponentStatus, ...]]:
    """Read every selected destination and present the lifecycle table."""
    report: dict[str, tuple[ComponentStatus, ...]] = {}
    for target in profile.targets:
        harness = get_harness(target)
        if "skills" in profile.components:
            root = resolve_destination(harness, profile.scope, home=home, project_root=project_root, kind="skills")
            report[f"{target}:skills"] = status_target(root, _desired_components(repo_root, harness, ("skills",), profile.with_data))
        if "agents" in profile.components and harness.user_agent_root is not None:
            root = resolve_destination(harness, profile.scope, home=home, project_root=project_root, kind="agents")
            report[f"{target}:agents"] = status_target(root, _desired_components(repo_root, harness, ("agents",), profile.with_data))
        if target == "opencode":
            config_root = (home / ".config/opencode") if profile.scope == "user" else project_root
            report["opencode:config"] = status_target(config_root, _opencode_config_component(config_root))
    if "codex" in profile.targets:
        package_root = _package_root(profile.scope, home=home, project_root=project_root)
        report["codex:package"] = status_target(package_root, _codex_package_components(repo_root))
    return report


def uninstall(
    profile: InstallProfile,
    *,
    home: Path,
    project_root: Path,
    force: bool = False,
) -> None:
    def remove_consumer(root: Path, harness_id: str) -> None:
        manifest = _manifest(root)
        statuses = status_target(root)
        modified = [item.component for item in statuses if item.state == "modified" and harness_id in item.harnesses]
        if modified and not force:
            raise ManagedContentModified("Locally modified managed content: " + ", ".join(modified))
        if not manifest["components"]:
            return
        stage = _stage_root(root)
        staged_root = stage / "root"
        staged_manifest = _manifest(staged_root)
        for key, record in list(staged_manifest["components"].items()):
            consumers = set(record.get("harnesses", ()))
            if harness_id not in consumers:
                continue
            consumers.remove(harness_id)
            if consumers:
                record["harnesses"] = sorted(consumers)
                continue
            for relative in record["paths"]:
                target_path = staged_root / _safe_relative(relative)
                if target_path.is_file() or target_path.is_symlink():
                    target_path.unlink()
            staged_manifest["components"].pop(key)
        manifest_path = staged_root / MANIFEST_NAME
        if staged_manifest["components"]:
            manifest_path.write_text(json.dumps(staged_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        elif manifest_path.exists():
            manifest_path.unlink()
        _commit_stage(root, stage)

    for target in profile.targets:
        harness = get_harness(target)
        for kind in profile.components:
            if kind == "agents" and harness.user_agent_root is None:
                continue
            root = resolve_destination(harness, profile.scope, home=home, project_root=project_root, kind=kind)  # type: ignore[arg-type]
            remove_consumer(root, target)
        if profile.scope == "user" and "skills" in profile.components and target == "opencode":
            shared_root = resolve_destination("codex", profile.scope, home=home, project_root=project_root, kind="skills")
            remove_consumer(shared_root, "opencode")
        if target == "opencode":
            config_root = (home / ".config/opencode") if profile.scope == "user" else project_root
            remove_consumer(config_root, "opencode")
        if target == "codex":
            remove_consumer(_package_root(profile.scope, home=home, project_root=project_root), "codex")


def _report(report: dict[str, tuple[ComponentStatus, ...]]) -> None:
    for location, statuses in report.items():
        for status in statuses:
            consumers = ",".join(status.harnesses) or "-"
            print(f"{location}\t{status.component}\t{status.state}\t{consumers}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--profile", default="default")
    parser.add_argument("--yes", action="store_true", help="Use a saved profile without prompts")
    parser.add_argument("--targets", help="Comma-separated harness ids for a noninteractive profile")
    parser.add_argument("--scope", choices=("user", "project"))
    parser.add_argument("--components", help="Comma-separated skills,agents")
    parser.add_argument("--with-data", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--prune", action="store_true")
    args = parser.parse_args()
    home = args.home.resolve()
    if args.yes:
        profile = load_profile(home, args.profile)
        if profile is None:
            if not (args.targets and args.scope and args.components):
                parser.error("--yes needs a saved profile or --targets, --scope, and --components")
            profile = InstallProfile(tuple(args.targets.split(",")), args.scope, tuple(args.components.split(",")), args.with_data, "force" if args.force else "ask")
        if args.with_data:
            profile = InstallProfile(profile.targets, profile.scope, profile.components, True, profile.overwrite)
    else:
        profile = interview(home)
        save_profile(home, profile, args.profile)
    if args.status:
        _report(status(profile, repo_root=args.repo_root.resolve(), home=home, project_root=args.project_root.resolve()))
        return 0
    if args.uninstall:
        uninstall(profile, home=home, project_root=args.project_root.resolve(), force=args.force)
        return 0
    if args.update and not args.yes and not args.force:
        modified = [
            item.component for items in status(profile, repo_root=args.repo_root.resolve(), home=home, project_root=args.project_root.resolve()).values()
            for item in items if item.state == "modified"
        ]
        if modified:
            args.force = _choice("Replace locally modified managed content (yes/no)", ("yes", "no"), "no") == "yes"
    report = install(profile, repo_root=args.repo_root.resolve(), home=home, project_root=args.project_root.resolve(), force=args.force, dry_run=args.dry_run, update=args.update, prune=args.prune)
    _report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
