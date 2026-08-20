#!/usr/bin/env python3
"""Report canonical and installed skills visible to each supported harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harness_contract import HARNESS_SPECS, simulate_skill_discovery
from skill_discovery import inventory


REPO_ROOT = Path(__file__).resolve().parent.parent


def records(repo_root: Path, *, home: Path | None = None, project_root: Path | None = None) -> list[dict[str, str]]:
    """Collect the canonical corpus plus configured harness discovery roots."""
    found = inventory(repo_root)
    result = [
        {"harness": "repository", "name": skill.name, "plugin": skill.plugin.name, "path": skill.path.relative_to(repo_root).as_posix()}
        for skill in found.skills
    ]
    for source in sorted((repo_root / ".claude/skills").glob("*/SKILL.md")):
        result.append({"harness": "claude-only", "name": source.parent.name, "plugin": "unshipped", "path": source.relative_to(repo_root).as_posix()})
    if home is None or project_root is None:
        return result
    for spec in HARNESS_SPECS:
        for root in simulate_skill_discovery(spec, cwd=project_root, home=home):
            for source in sorted(root.glob("*/SKILL.md")):
                result.append({"harness": spec.id, "name": source.parent.name, "plugin": "installed", "path": source.as_posix()})
    return result


def _table(items: list[dict[str, str]]) -> str:
    rows = [[item["harness"], item["plugin"], item["name"], item["path"]] for item in items]
    try:
        from tabulate import tabulate

        return tabulate(rows, headers=("Harness", "Plugin", "Skill", "Path"), tablefmt="plain")
    except ImportError:
        return "\n".join("\t".join(row) for row in [["Harness", "Plugin", "Skill", "Path"], *rows])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--home", type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output = records(args.repo_root.resolve(), home=args.home.resolve() if args.home else None, project_root=args.project_root.resolve() if args.project_root else None)
    print(json.dumps(output, indent=2, ensure_ascii=False) if args.json else _table(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
