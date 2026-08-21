# Installation

Claude Code and Codex CLI are the primary paths. OpenCode receives a
best-effort compatibility installation through the same installer.
The installer design and maintenance invariants are specified in the
[Fork Contract](FORK_CONTRACT.md).

Requires Python 3.12 and PyYAML 6 or newer.

## Claude marketplace

```text
/plugin marketplace add OWASP/secure-agent-playbook
/plugin install code-security-skills@agent-security-playbook
/plugin install ai-security-skills@agent-security-playbook
```

## Installer

Run the fresh interview to choose targets and user or project scope. Every
selected harness receives the complete skills-and-agents bundle:

```sh
./install.py
```

The same interview runs every time. Nothing is saved between invocations:

```sh
./install.py
./install.py --uninstall
```

A no-argument run treats the checkout as authoritative and replaces the
selected skill and agent paths. `--uninstall` needs no interview; it finds
known skills by `SKILL.md` and known agent filenames across the
supported destinations. It reports every destination it removed files from,
then prints the total number of removed skill and agent paths.

Install likewise prints every destination it writes. Codex skills are grouped
under its own `secure-agent-playbook/` subdirectory; Claude skills remain flat.

The installer writes only skills and agents. It creates no saved profile,
ownership manifest, package copy, or harness configuration.

Standalone skills use the following locations:

| Harness | User skills | Project skills | Agents |
| --- | --- | --- | --- |
| Claude Code | `~/.claude/skills` | `.claude/skills` | `.claude/agents/*.md` |
| Codex CLI | `~/.codex/skills/secure-agent-playbook` | `.codex/skills/secure-agent-playbook` | `.codex/agents/*.toml` |
| OpenCode compatibility | `~/.config/opencode/skills` | `.opencode/skills` | `.opencode/agents/*.md` |

Every standalone skill installation materializes the datasets it cites below
its `references/data/` directory.

## Verify install

```sh
./install.py
```

A successful run ends with an installed count and exact path for each selected
location. Restart Codex if newly installed skills are not visible immediately.
