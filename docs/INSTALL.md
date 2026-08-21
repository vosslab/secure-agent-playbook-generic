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
selected skill, resource, and agent paths. `--uninstall` needs no interview;
it finds known skills by `SKILL.md`, the uniquely named resource tree, and
known agent filenames across the supported destinations. It reports every
destination it removed files from, then prints the total number of removed
skill, resource, and agent paths.

Install likewise prints every destination it writes. All Codex skills live in
one `secure-agent-playbook/` group; Claude skills remain flat.

The installer writes only skills, agents, and their required shared resources.
It creates no saved profile, ownership manifest, or harness configuration.

Standalone skills use the following locations:

| Harness | User skills | Project skills | Agents |
| --- | --- | --- | --- |
| Claude Code | `~/.claude/skills` | `.claude/skills` | `.claude/agents/*.md` |
| Codex CLI | `~/.codex/skills/secure-agent-playbook` | `.codex/skills/secure-agent-playbook` | `.codex/agents/*.toml` |
| OpenCode compatibility | `~/.config/opencode/skills` | `.opencode/skills` | `.opencode/agents/*.md` |

Datasets are copied once per selected harness, not once per skill. For Codex,
the shared tree is `secure-agent-playbook/resources/`. Each skill contains
relative `plays`, `templates`, and `data` symlinks into that tree. Claude and
OpenCode use the same links with a uniquely named shared resource directory
beside their flat skill directories. Resource directories contain no
`SKILL.md`, so harnesses do not discover them as skills.

## Verify install

```sh
./install.py
```

A successful run ends with an installed count and exact path for each selected
location. Restart Codex if newly installed skills are not visible immediately.
