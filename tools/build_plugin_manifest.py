"""Render the README harness table and validate canonical plugin metadata.

Codex/OpenCode package files are installer-owned. The installer builds them in
its target staging directory from the public helpers in this module.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

from build_skills_index import write_or_check as write_skills_index
from harness_contract import render_support_table
from skill_discovery import inventory


REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED_BY = "tools/build_plugin_manifest.py"
TABLE_MARKER = re.compile(r"<!-- harness-support:start -->.*?<!-- harness-support:end -->", re.DOTALL)


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def _interface(plugin: Any) -> dict[str, Any]:
    return {
        "displayName": plugin.name.replace("-", " ").title(),
        "shortDescription": plugin.description,
        "longDescription": plugin.description,
        "category": "security",
        "capabilities": ["skills", "agents"],
        "defaultPrompt": f"Use {plugin.name} to perform an evidence-based security review.",
        "websiteURL": plugin.homepage or "",
    }


def codex_manifest(plugin: Any) -> dict[str, Any]:
    return {
        "generated_by": GENERATED_BY,
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "skills": "./skills/",
        "interface": _interface(plugin),
    }


def marketplace(found: Any) -> dict[str, Any]:
    return {
        "generated_by": GENERATED_BY,
        "name": "agent-security-playbook",
        "plugins": [
            {
                "name": plugin.name,
                "source": f"./plugins/{plugin.path.name}",
                "description": plugin.description,
                "version": plugin.version,
            }
            for plugin in found.plugins
        ],
    }


def opencode_config(existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the installer-owned OpenCode configuration from optional settings."""
    existing = dict(existing or {})
    permission = existing.get("permission")
    if not isinstance(permission, dict):
        permission = {}
    permission["skill"] = "allow"
    existing["generated_by"] = GENERATED_BY
    existing["permission"] = permission
    return existing


def generated_files(repo_root: Path = REPO_ROOT) -> dict[Path, str]:
    repo_root = repo_root.resolve()
    found = inventory(repo_root)
    files: dict[Path, str] = {}
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    replacement = f"<!-- harness-support:start -->\n{render_support_table()}\n<!-- harness-support:end -->"
    if not TABLE_MARKER.search(readme):
        raise ValueError("README.md is missing the generated harness-support markers")
    files[Path("README.md")] = TABLE_MARKER.sub(replacement, readme)
    return files


def validate_claude_manifests(repo_root: Path = REPO_ROOT) -> list[str]:
    """Validate source manifests without claiming ownership or rewriting them."""
    repo_root = repo_root.resolve()
    found = inventory(repo_root)
    errors: list[str] = []
    required = ("name", "description", "version", "author", "homepage", "repository", "license", "keywords")
    for plugin in found.plugins:
        for key in required:
            if not plugin.manifest.get(key):
                errors.append(f"{plugin.manifest_path}: missing {key}")
        if plugin.manifest.get("name") != plugin.name or plugin.manifest.get("version") != plugin.version:
            errors.append(f"{plugin.manifest_path}: identity differs from PluginMeta")
    root_manifest_path = repo_root / ".claude-plugin/plugin.json"
    root_manifest = json.loads(root_manifest_path.read_text(encoding="utf-8"))
    for key in required:
        if key not in root_manifest:
            errors.append(f"{root_manifest_path}: missing {key}")
    if found.plugins:
        reference = found.plugins[0].manifest
        for key in ("version", "author", "homepage", "repository", "license"):
            if root_manifest.get(key) != reference.get(key):
                errors.append(f"{root_manifest_path}: {key} differs from plugin manifests")
    marketplace_path = repo_root / ".claude-plugin/marketplace.json"
    marketplace_data = json.loads(marketplace_path.read_text(encoding="utf-8"))
    entries = {item.get("name"): item.get("source") for item in marketplace_data.get("plugins", []) if isinstance(item, dict)}
    for plugin in found.plugins:
        expected_source = f"./plugins/{plugin.path.name}/"
        if entries.get(plugin.name) != expected_source:
            errors.append(f"{marketplace_path}: source for {plugin.name} differs ({entries.get(plugin.name)!r})")
    return errors


def write_or_check(repo_root: Path = REPO_ROOT, *, check: bool = False) -> bool:
    repo_root = repo_root.resolve()
    errors = validate_claude_manifests(repo_root)
    if errors:
        raise ValueError("\n".join(errors))
    expected = generated_files(repo_root)
    clean = True
    for relative, content in expected.items():
        target = repo_root / relative
        if check:
            clean = target.is_file() and target.read_text(encoding="utf-8") == content and clean
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    return clean and write_skills_index(repo_root, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "check", "validate"), nargs="?", default="build")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    if args.command == "validate":
        errors = validate_claude_manifests(args.repo_root)
        if errors:
            print("\n".join(errors))
            return 1
        return 0
    clean = write_or_check(args.repo_root, check=args.command == "check")
    if not clean:
        print("Generated portable surfaces are stale; run tools/build_plugin_manifest.py build")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
