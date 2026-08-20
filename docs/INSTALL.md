# Installation

Claude Code and Codex CLI are the primary paths. OpenCode receives a
best-effort compatibility installation through the same installer.

## Claude marketplace

```text
/plugin marketplace add OWASP/secure-agent-playbook
/plugin install code-security-skills@agent-security-playbook
/plugin install ai-security-skills@agent-security-playbook
```

## Installer

Run once to choose targets, scope, skills/agents, and dataset policy:

```sh
python3 tools/install_skills.py
```

The saved profile at `~/.config/agent-security-playbook/profile.json` supports
repeatable, prompt-free runs:

```sh
python3 tools/install_skills.py --yes
python3 tools/install_skills.py --yes --with-data
python3 tools/install_skills.py --yes --status
python3 tools/install_skills.py --yes --update
python3 tools/install_skills.py --yes --uninstall
```

For Codex, the installer first creates a complete package in its target-owned
package directory, copies each canonical plugin, generates
`.codex-plugin/plugin.json` there, and writes a local `marketplace.json`.
Import that package through the Codex Plugins interface. The repository stays
free of harness-specific package output.

Standalone skills use the following locations:

| Harness | User skills | Project skills | Agents |
| --- | --- | --- | --- |
| Claude Code | `~/.claude/skills` | `.claude/skills` | Marketplace agents |
| Codex CLI | `~/.agents/skills` | `.agents/skills` | `.codex/agents/*.toml` |
| OpenCode compatibility | `~/.config/opencode/skills` | `.opencode/skills` | `.opencode/agent/*.md` |

`--with-data` materializes each cited plugin dataset below the installed
skill's `references/data/` directory. Normal installs retain a source-location
note instead. The installer protects locally modified managed files and uses
`--force` for deliberate replacement.
