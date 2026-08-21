# Fork Contract

This repository is a small, patch-style fork of the OWASP Secure Agent
Playbook. Its purpose is to make the existing playbook portable across agent
harnesses without turning the fork into a separate framework or maintaining a
second copy of the security content.

Here, **generic** means harness-neutral discovery, conversion, and installation.
It does not mean removing the playbook's OWASP focus or
rewriting canonical skills and plays into a new abstraction.

## Source boundaries

- `README.md` is the only upstream-inherited file this fork intentionally
  edits. It must identify the fork clearly and route readers to fork-owned
  installation and maintenance documentation.
- Do not add fork policy to upstream-inherited guidance or content files such
  as `CLAUDE.md`, canonical skills, plays, templates, agents, or datasets.
- `plugins/`, their skills, plays, templates, agents, and plugin-local data
  remain the canonical content layout.
- `data/` remains the repository-level reference collection. Any part cited by
  an installed skill becomes required installation content.
- `install.py` is the public standalone entrypoint and contains the complete
  installer flow; do not bury a second installer entrypoint under `tools/`.
- `install_lib/` contains only metadata, resource, and agent-conversion helpers
  imported by the root installer. Harness destinations remain in `install.py`.

Prefer changes at these adapter boundaries. Do not fork a skill or play merely
to accommodate a harness path or agent format.

## Installer contract

Every install invocation asks for its topology afresh:

- target harnesses;
- user or project scope;
- final confirmation.

Responses are never cached or saved. `--uninstall` does not ask topology
questions; it searches the known destinations for canonical skill and agent key
files.

Every harness offered by the interview installs both skills and agents. There
is no component override, and neither half of the bundle may be silently
disabled by a missing destination entry. Claude agents are
copied unchanged from their canonical Markdown; only non-Claude formats are
converted.

All Codex skills live directly under
`.codex/skills/secure-agent-playbook/`, while Claude skills remain flat because
Claude does not support grouped skill directories. Converted agent filenames
and internal names use the canonical short agent name without a plugin prefix.

The public CLI is deliberately limited to options users may need to change
between runs:

| Option | Purpose |
| --- | --- |
| `--uninstall` | Remove known installed skills, resources, and agents. |

Before adding an argument, require evidence that users frequently need it.
Topology belongs in the fresh interview. Internal paths belong in Python
function parameters. Automatic behavior and required resources must not become
flags.

In particular, do not add profile saving or dataset, dry-run, force, status,
update, pruning, repository-root, home, project-root, target, scope, component,
or confirmation flags.

## Required data and shared resources

The datasets are runtime inputs to these skills, not optional examples or
supplemental documentation. Skills consult the local ASVS, FIASSE, MASVS,
MASTG, AISVS, LLM Top 10, OpenCRE, and secure-code reference files to select
controls, follow review procedures, and produce traceable findings. Installing
a `SKILL.md` without the data it names leaves the skill incomplete and can
cause omitted controls, unsupported conclusions, or invented substitutes.

The settled design is one self-contained resource copy per selected harness,
not one copy per skill and not links back to the Git checkout:

- merge plugin-local and repository-level content into one shared `plays/`,
  `templates/`, and `data/` tree;
- place the Codex tree at
  `.codex/skills/secure-agent-playbook/resources/`;
- place a uniquely named resource tree beside the flat Claude and OpenCode
  skill directories;
- add relative `plays`, `templates`, and `data` symlinks inside every skill so
  canonical logical paths keep working at user and project scope;
- reject conflicting files during the merge instead of silently choosing one.

This keeps one installed source of truth while allowing every skill to read
the required files through its own directory. Moving or deleting the checkout
after installation does not break the installed skills.

This is an invariant, not a default:

- there is no `--with-data` or inverse option;
- there is no saved installer state;
- resolver APIs have no reduced or thin materialization mode;
- installed Markdown references and skill resource links must resolve inside
  the selected harness installation;
- shared resource directories contain no `SKILL.md` and must not appear as
  discoverable skills.

## Clean installation

The Git checkout is authoritative and installed copies are disposable. Each
install replaces the selected known skill directories, shared resource tree,
and agent files directly. It does not write profiles, receipts, ownership
manifests, harness configuration, or any other hidden state.

Unrelated destination entries are untouched, including symbolic links outside
the selected skill or agent names. Uninstall removes canonical skill
directories containing `SKILL.md`, the uniquely named shared resource tree,
and canonical agent filenames.

## Adding another harness

Add harness behavior at the two existing adapter points:

1. Add the user and project skill/agent roots to `DESTINATIONS` in `install.py`.
2. Add the smallest required branch to `_agent_content()`.
3. Reuse canonical inventory and complete resource materialization.
4. Keep harness-specific output outside the source tree.
5. Add an interview target only when the adapter is genuinely supported.

Do not add one CLI flag per harness capability. Differences belong in those
two adapter points.

## Patch maintenance and validation

Keep fork changes narrow, easy to review against upstream, and concentrated in
fork-owned compatibility files and documentation. Apart from `README.md`, do
not modify upstream-inherited files. Avoid unrelated formatting or
canonical-content edits during upstream synchronization.

Do not add fork-specific test scripts to this patch-style repository. Validate
with existing upstream checks and ephemeral commands or temporary directories.
At minimum, check:

- `./install.py --help` exposes only `--uninstall`;
- removed options, especially `--with-data`, are rejected;
- every applicable run conducts a fresh interview and saves nothing;
- every installed skill resolves its cited datasets through the shared links;
- install writes only skills, resources, and agents, while uninstall finds
  their known paths;
- Python compilation, static checks, and `git diff --check` remain clean.

When this contract changes intentionally, update this document and the affected
fork-owned code or documentation in the same patch. Change `README.md` only
when the fork identity, first-success path, or documentation routes change;
installer detail belongs in `docs/INSTALL.md`.
