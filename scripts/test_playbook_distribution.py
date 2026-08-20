"""Hermetic contract tests for portable playbook distribution."""

from __future__ import annotations

import json
from pathlib import Path
import dataclasses
import shutil
import sys
import tempfile
import tomllib
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from build_plugin_manifest import write_or_check
from convert_agents import to_codex_toml, to_opencode_md
from harness_contract import CLAUDE, CODEX, OPENCODE, resolve_destination, simulate_skill_discovery
from install_skills import InstallProfile, ManagedContentModified, install, interview, load_profile, save_profile, status, status_target, uninstall
from resource_resolver import ResourceResolutionError, installed_form
from skill_discovery import inventory


class PlaybookDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = inventory(ROOT)

    def test_inventory_matches_canonical_source(self) -> None:
        self.assertEqual((len(self.inventory.plugins), len(self.inventory.skills), len(self.inventory.agents)), (2, 17, 6))
        self.assertTrue(all(skill.name and skill.description for skill in self.inventory.skills))

    def test_harness_simulator_reaches_declared_roots_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            work = root / "nested/work"
            home = Path(temporary) / "home"
            for path in (
                root / ".claude/skills/project-claude/SKILL.md",
                root / ".agents/skills/project-codex/SKILL.md",
                root / ".opencode/skills/project-open/SKILL.md",
                home / ".claude/skills/user-claude/SKILL.md",
                home / ".agents/skills/user-codex/SKILL.md",
                home / ".config/opencode/skills/user-open/SKILL.md",
                root / "skills/decoy/SKILL.md",
                root.parent / ".agents/skills/outside/SKILL.md",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("---\nname: fixture\ndescription: fixture\n---\n", encoding="utf-8")
            work.mkdir(parents=True)
            self.assertIn((root / ".claude/skills").resolve(), simulate_skill_discovery(CLAUDE, cwd=work, home=home, repo_root=root))
            self.assertIn((home / ".agents/skills").resolve(), simulate_skill_discovery(CODEX, cwd=work, home=home, repo_root=root))
            open_roots = simulate_skill_discovery(OPENCODE, cwd=work, home=home, repo_root=root)
            self.assertIn((root / ".opencode/skills").resolve(), open_roots)
            self.assertIn((root / ".agents/skills").resolve(), open_roots)
            self.assertNotIn((root / "skills").resolve(), open_roots)
            self.assertNotIn((root.parent / ".agents/skills").resolve(), open_roots)
            self.assertEqual(resolve_destination(CODEX, "user", home=home, project_root=root, kind="agents"), home / ".codex/agents")
            self.assertEqual(resolve_destination(OPENCODE, "project", home=home, project_root=root, kind="agents"), root / ".opencode/agent")

    def test_resolver_is_pure_for_all_canonical_skills(self) -> None:
        before = {skill.path: skill.path.read_bytes() for skill in self.inventory.skills}
        for skill in self.inventory.skills:
            thin = installed_form(skill)
            full = installed_form(skill, with_data=True)
            self.assertIn(Path("SKILL.md"), {Path(item) for item in thin.files})
            self.assertEqual(thin.text, installed_form(skill).text)
            self.assertGreaterEqual(len(full.files), len(thin.files))
            if full.data_file_count:
                self.assertTrue(any(b"references/data" in content for content in full.files.values()))
        self.assertEqual(before, {skill.path: skill.path.read_bytes() for skill in self.inventory.skills})

    def test_agent_formats_parse(self) -> None:
        for agent in self.inventory.agents:
            codex = tomllib.loads(to_codex_toml(agent))
            self.assertEqual(codex["sandbox_mode"], "read-only")
            self.assertTrue(all(codex[key] for key in ("name", "description", "developer_instructions")))
            self.assertTrue(to_opencode_md(agent).startswith("---\n"))
        hostile = dataclasses.replace(self.inventory.agents[0], body='A literal """ and a backslash \\ survive.\nTrailing quote: "')
        self.assertIn(hostile.body, tomllib.loads(to_codex_toml(hostile))["developer_instructions"])

    def test_generated_surfaces_are_clean(self) -> None:
        self.assertTrue(write_or_check(ROOT, check=True))

    def test_scripted_interview_persists_a_yes_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            with mock.patch("builtins.input", side_effect=("codex", "user", "skills", "no", "ask", "yes")):
                profile = interview(home)
            save_profile(home, profile)
            self.assertEqual(load_profile(home), profile)

    def test_generator_rejects_seeded_drift_and_missing_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "repo"
            for name in ("plugins", ".claude-plugin", ".claude"):
                shutil.copytree(ROOT / name, fixture / name)
            for name in ("CLAUDE.md", "README.md"):
                shutil.copy2(ROOT / name, fixture / name)
            write_or_check(fixture)
            (fixture / "README.md").write_text((fixture / "README.md").read_text(encoding="utf-8").replace("| Claude Code | Primary |", "| Claude Code | Drift |"), encoding="utf-8")
            self.assertFalse(write_or_check(fixture, check=True))
            write_or_check(fixture)
            skill = fixture / "plugins/code-security-skills/skills/sca-audit/SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8").replace("plays/sca-audit.md", "plays/missing.md"), encoding="utf-8")
            with self.assertRaises(ResourceResolutionError):
                installed_form(next(item for item in inventory(fixture).skills if item.name == "sca-audit"))

    def test_installer_states_and_recovery_are_hermetic(self) -> None:
        profile = InstallProfile(("claude", "codex", "opencode"), "user", ("skills", "agents"), False, "ask")
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            decoy = home / ".agents/skills/third-party/SKILL.md"
            decoy.parent.mkdir(parents=True, exist_ok=True)
            decoy.write_text("third party", encoding="utf-8")
            report = install(profile, repo_root=ROOT, home=home, project_root=Path(temporary) / "project")
            self.assertTrue(all(item.state == "current" for items in report.values() for item in items))
            self.assertEqual(decoy.read_text(encoding="utf-8"), "third party")
            package = home / ".config/agent-security-playbook/packages"
            self.assertTrue((package / "plugins/code-security-skills/.codex-plugin/plugin.json").is_file())
            self.assertTrue((package / "marketplace.json").is_file())
            self.assertTrue(any(item.state == "current" for items in status(profile, repo_root=ROOT, home=home, project_root=Path(temporary) / "project").values() for item in items))
            modified = home / ".agents/skills/sca-audit/SKILL.md"
            modified.write_text(modified.read_text(encoding="utf-8") + "\nlocal note\n", encoding="utf-8")
            with self.assertRaises(ManagedContentModified):
                install(profile, repo_root=ROOT, home=home, project_root=Path(temporary) / "project")
            install(profile, repo_root=ROOT, home=home, project_root=Path(temporary) / "project", update=True)
            self.assertIn("local note", modified.read_text(encoding="utf-8"))
            install(profile, repo_root=ROOT, home=home, project_root=Path(temporary) / "project", force=True)
            self.assertNotIn("local note", modified.read_text(encoding="utf-8"))
            uninstall(profile, home=home, project_root=Path(temporary) / "project", force=True)
            self.assertEqual(decoy.read_text(encoding="utf-8"), "third party")

    def test_shared_codex_opencode_consumer_survives_single_uninstall(self) -> None:
        both = InstallProfile(("codex", "opencode"), "user", ("skills",), False, "ask")
        only_open = InstallProfile(("opencode",), "user", ("skills",), False, "ask")
        only_codex = InstallProfile(("codex",), "user", ("skills",), False, "ask")
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            project = Path(temporary) / "project"
            install(both, repo_root=ROOT, home=home, project_root=project)
            shared_manifest = json.loads((home / ".agents/skills/.agent-security-playbook.json").read_text(encoding="utf-8"))
            self.assertEqual(shared_manifest["components"]["skill:sca-audit"]["harnesses"], ["codex", "opencode"])
            uninstall(only_open, home=home, project_root=project)
            self.assertTrue((home / ".agents/skills/sca-audit/SKILL.md").is_file())
            self.assertTrue(all(item.state == "current" for item in status(only_codex, repo_root=ROOT, home=home, project_root=project)["codex:skills"]))

    def test_state_classifier_covers_all_lifecycle_states(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "skills"
            root.mkdir()
            managed = root / "one/SKILL.md"
            managed.parent.mkdir()
            managed.write_text("old", encoding="utf-8")
            digest = __import__("hashlib").sha256(b"old").hexdigest()
            (root / ".agent-security-playbook.json").write_text(json.dumps({"schema_version": 1, "components": {"skill:one": {"paths": {"one/SKILL.md": digest}, "harnesses": ["codex"]}}}), encoding="utf-8")
            desired = {"skill:one": {Path("one/SKILL.md"): b"old"}}
            self.assertEqual(status_target(root, desired)[0].state, "current")
            self.assertEqual(status_target(root, {"skill:one": {Path("one/SKILL.md"): b"new"}})[0].state, "outdated")
            managed.write_text("local", encoding="utf-8")
            self.assertEqual(status_target(root, desired)[0].state, "modified")
            managed.unlink()
            self.assertEqual(status_target(root, desired)[0].state, "missing")
            managed.write_text("old", encoding="utf-8")
            self.assertEqual(status_target(root)[0].state, "orphaned")


if __name__ == "__main__":
    unittest.main()
