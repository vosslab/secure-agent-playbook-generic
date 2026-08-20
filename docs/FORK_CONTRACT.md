# Fork Contract

This repository is a small, patch-style fork of the OWASP Secure Agent
Playbook. Its purpose is to make the existing playbook portable across agent
harnesses without turning the fork into a separate framework or maintaining a
second copy of the security content.

Here, **generic** means harness-neutral discovery, packaging, installation, and
lifecycle management. It does not mean removing the playbook's OWASP focus or
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
- `install.py` is the public standalone entrypoint.
- `tools/harness_contract.py`, discovery, conversion, manifest, resolver, and
  installer modules form the compatibility layer around canonical content.
- Harness-specific packages are generated in installer-owned destinations;
  generated package trees do not belong in the repository.

Prefer changes at these adapter boundaries. Do not fork a skill or play merely
to accommodate a harness path or manifest format.

## Installer contract

The first run asks only for stable installation topology:

- target harnesses;
- user or project scope;
- skills, agents, or both;
- final confirmation.

Those choices are saved in one profile at
`~/.config/agent-security-playbook/profile.json`. A later bare `./install.py`
run automatically reuses that profile, installs repository updates, and prunes
obsolete unmodified managed files.

The public CLI is deliberately limited to options users may need to change
between runs:

| Option | Purpose |
| --- | --- |
| `--dry-run` | Preview an installation without writing it. |
| `--force` | Deliberately replace locally modified managed content. |
| `--status` | Report managed component state. |
| `--uninstall` | Remove components owned by the saved profile. |

Before adding an argument, require evidence that users frequently change the
value between runs. Stable topology belongs in the first-run profile. Internal
paths belong in Python function parameters. Automatic behavior and required
resources must not become flags.

In particular, do not restore dataset, update, pruning, named-profile,
repository-root, home, project-root, target, scope, component, or confirmation
flags. Older profile keys such as `with_data` and `overwrite` are accepted only
as ignored input so existing installations migrate safely.

## Datasets are required

A skill is not complete without the local datasets it cites. Standalone
materialization therefore computes the transitive local resource closure and
always includes both plugin-local and cited repository-level data under the
installed skill's `references/data/` tree.

This is an invariant, not a default:

- there is no `--with-data` or inverse option;
- the saved profile has no dataset setting;
- resolver APIs have no reduced or thin materialization mode;
- installed Markdown must resolve its rewritten local references inside the
  materialized skill tree.

## Ownership and update safety

The installer owns only paths recorded in its manifest. Writes are assembled
in a staging directory and committed by rename. A normal rerun updates managed
content, removes clean orphans, and preserves locally modified files. Only an
explicit per-run `--force` may replace modified managed content.

Do not store an overwrite policy in the profile. A past choice must never make
a future update destructive by default.

## Adding another harness

Add harness behavior through the existing contract and conversion modules:

1. Define discovery roots and supported component formats.
2. Add the smallest required manifest or agent conversion.
3. Reuse canonical inventory and complete resource materialization.
4. Keep harness-specific output outside the source tree.
5. Add a first-run target choice only when the adapter is genuinely supported.

Do not add one CLI flag per harness capability. Differences should be encoded
in the harness contract.

## Patch maintenance and validation

Keep fork changes narrow, easy to review against upstream, and concentrated in
fork-owned compatibility files and documentation. Apart from `README.md`, do
not modify upstream-inherited files. Avoid unrelated formatting or
canonical-content edits during upstream synchronization.

Do not add fork-specific test scripts to this patch-style repository. Validate
with existing upstream checks and ephemeral commands or temporary directories.
At minimum, check:

- `./install.py --help` exposes only the four public switches;
- removed options, especially `--with-data`, are rejected;
- legacy profiles load without restoring obsolete behavior;
- every installed skill contains its cited datasets;
- ordinary updates preserve modified files and `--force` is explicit;
- Python compilation, static checks, manifest validation, and
  `git diff --check` remain clean.

When this contract changes intentionally, update this document, the nearby
installer comments, `docs/INSTALL.md`, and the README in the same patch.
