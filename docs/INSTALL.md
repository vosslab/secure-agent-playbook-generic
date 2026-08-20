# Installation

Claude Code and Codex CLI are the primary paths. OpenCode receives a
best-effort compatibility installation through the same installer.
The installer design and maintenance invariants are specified in the
[Fork Contract](FORK_CONTRACT.md).

## Claude marketplace

```text
/plugin marketplace add OWASP/secure-agent-playbook
/plugin install code-security-skills@agent-security-playbook
/plugin install ai-security-skills@agent-security-playbook
```

## Installer

Run once to choose targets, scope, and skills/agents:

```sh
./install.py
```

The saved profile at `~/.config/agent-security-playbook/profile.json` makes a
bare rerun install repository updates without repeating the interview:

```sh
./install.py
./install.py --status
./install.py --dry-run
./install.py --uninstall
```

A no-argument rerun installs repository updates, removes obsolete unmodified
managed files, and preserves locally modified managed files. Pass `--force`
only when those local changes should be replaced deliberately.

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

Every standalone skill installation materializes the datasets it cites below
its `references/data/` directory. The installer protects locally modified
managed files and uses `--force` for deliberate replacement.
