# Secure Agent Playbook — Generic Harness Fork

An installation-focused security playbook fork for developers and security reviewers, delivering complete skills, agents, plays, and cited datasets to Claude Code, Codex, and OpenCode through one safe installer.

> **Fork notice:** This is the multi-harness
> [`vosslab/secure-agent-playbook-generic`](https://github.com/vosslab/secure-agent-playbook-generic)
> fork, not the canonical
> [`OWASP/secure-agent-playbook`](https://github.com/OWASP/secure-agent-playbook).
> It keeps the upstream security corpus recognizable and concentrates fork
> behavior in the portability layer described by the
> [Fork Contract](docs/FORK_CONTRACT.md).

## Table of Contents

- [One Corpus, Native to Each Harness](#one-corpus-native-to-each-harness)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Skills Catalog](#skills-catalog)
- [Agents](#agents)
- [Example Output](#example-output)
- [Plays](#plays)
- [Architecture](#architecture)
- [OWASP Foundation](#owasp-foundation)
- [Related Projects](#related-projects)
- [Contributing](#contributing)
- [License](#license)

## One Corpus, Native to Each Harness

One canonical security corpus is installed where each supported agent already
looks. The fork adapts paths and agent formats without maintaining divergent
copies of the OWASP-grounded skills and plays.

- **Complete by construction** — Every standalone skill includes its referenced
  play, templates, and all cited plugin or repository datasets. There is no
  reduced installation mode.
- **Harness-native delivery** — Claude Code and Codex are primary targets;
  OpenCode is an explicit best-effort compatibility surface.
- **Fresh and explicit** — Every run asks where to install, treats the checkout
  as authoritative, and writes only the selected harness bundle—skills,
  agents, and required resources—with no saved profile, hidden manifest, or
  harness configuration.
- **Actionable security output** — The 17 skills and 6 agents produce findings
  with severity, CWE, evidence, remediation, and OWASP/OpenCRE traceability.
- **Upstream-shaped content** — The fork changes distribution behavior while
  keeping canonical plugins, skills, plays, templates, agents, and datasets in
  their familiar layout.

This remains a playbook rather than a framework or library. Agents follow its
procedures to perform code, dependency, infrastructure, mobile, LLM, MCP, and
multi-agent security work using consistent methodology.

| Harness | Support | User skills | Project skills | Agents |
| --- | --- | --- | --- | --- |
| Claude Code | Primary | `~/.claude/skills` | `.claude/skills` | `.claude/agents` |
| Codex CLI | Primary | `~/.codex/skills/secure-agent-playbook` | `.codex/skills/secure-agent-playbook` | `.codex/agents` |
| OpenCode (compatibility) | Best-effort compatibility | `~/.config/opencode/skills` | `.opencode/skills` | `.config/opencode/agents` |

## Quick Start

The generic installer requires a local checkout, Python 3.12, and
PyYAML 6 or newer. Install the declared Python dependency, then run the single
public entrypoint:

```sh
git clone https://github.com/vosslab/secure-agent-playbook-generic.git
cd secure-agent-playbook-generic
python3 -m pip install -r scripts/requirements.txt
./install.py
```

Choose the target harnesses and scope when prompted. A successful
install reports a short installed count and exact path for each selected
location; then ask the selected harness for a real result:

```text
Review src/auth/ for security issues.
```

See [Installation](docs/INSTALL.md) for destinations, reinstalling,
uninstalling, Claude marketplace alternatives, and organization deployment.
Without installing, any agent can follow a play directly from `plugins/*/plays/`.

## Documentation

- [`docs/INSTALL.md`](docs/INSTALL.md) — installer prompts, destinations, and
  uninstall behavior.
- [`docs/FORK_CONTRACT.md`](docs/FORK_CONTRACT.md) — compatibility boundaries,
  minimalist CLI policy, mandatory datasets, and upstream-sync rules.
- [`examples/README.md`](examples/README.md) — representative reports and
  deliberately vulnerable review fixtures.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — upstream-shaped play, skill, agent, and
  reference-data contribution guidance.

## Skills Catalog

### Code & Infrastructure Security (`code-security-skills`)

| Skill | What It Does | Say This | OWASP Ref |
|-------|-------------|----------|-----------|
| `code-review-security` | Security code review mapped to Top 10 + ASVS | "Review this code for security issues" | Top 10, ASVS |
| `sca-audit` | Dependency CVE scanning with reachability analysis | "Scan my dependencies for CVEs" | A06:2021 |
| `secrets-scan` | Detect hardcoded credentials and API keys | "Scan for hardcoded secrets" | CWE-798 |
| `api-security-review` | API review against OWASP API Top 10 (2023) | "Review this API for security" | API Top 10 |
| `web-security-review` | Web app review against OWASP Top 10 (2021) | "Review this web app for OWASP Top 10" | Top 10 |
| `mobile-code-review` | Native Android/iOS source review against OWASP MASVS v2.1.0 | "Review this mobile app for security" | MASVS v2.1.0 |
| `iac-security-review` | IaC security (Terraform, K8s, CloudFormation) | "Review this Terraform for security" | CIS Benchmarks |
| `securability-engineering` | Generate inherently securable code (FIASSE v1.0.4) | "Generate secure code for..." | FIASSE v1.0.4 |
| `securability-engineering-review` | Assess code securability (0-10 SSEM scoring) | "Assess the securability of this code" | FIASSE v1.0.4/SSEM |
| `prd-securability-enhancement` | Harden PRDs/specs with ASVS coverage and FIASSE SSEM requirements before code is written | "Harden this PRD" / "Map features to ASVS" | ASVS, FIASSE v1.0.4 |
| `security-guidance` | Auto-triggered ASVS guidance for security-sensitive code | *(auto-triggered)* | ASVS 5.0 |

### AI & Agent Security (`ai-security-skills`)

| Skill | What It Does | Say This | OWASP Ref |
|-------|-------------|----------|-----------|
| `agent-security-audit` | Audit agent permissions, injection surfaces, data exfil paths | "Audit this agent's security" | LLM Top 10 |
| `llm-risk-assess` | LLM app assessment against LLM Top 10 2025 | "Assess LLM risks for this app" | LLM Top 10 |
| `agentic-ai-risk-assess` | Agentic app assessment against Top 10 Agentic 2026 | "Assess agentic AI risks" | Agentic Top 10 |
| `mcp-server-review` | MCP server security review | "Review this MCP server" | LLM Top 10 |
| `prompt-injection-test` | Prompt injection testing (Arcanum PI Taxonomy) | "Test for prompt injection" | LLM01 |
| `multi-agentic-threat-model` | CSA MAESTRO 7-layer threat modeling | "Model threats for this multi-agent system" | CSA MAESTRO |

## Agents

Agents are autonomous security specialists that invoke skills and produce structured reports. Each agent has a focused system prompt, scoped tool access, and preloaded skills. Use them individually or as a coordinated team.

| Agent | Focus | Skills Invoked |
|-------|-------|---------------|
| `code-security-reviewer` | Code vulnerabilities, secrets, web security | code-review-security, secrets-scan, web-security-review |
| `dependency-auditor` | Supply chain and dependency CVE risks | sca-audit |
| `api-security-reviewer` | API security against OWASP API Top 10 | api-security-review |
| `mobile-security-reviewer` | Native Android/iOS source against OWASP MASVS v2.1.0 | mobile-code-review |
| `ai-security-assessor` | Agent configs, MCP servers, LLM app risks | agent-security-audit, mcp-server-review, llm-risk-assess, prompt-injection-test |
| `security-team-lead` | Coordinates specialists, consolidates report | securability-engineering-review |

**Standalone usage** — invoke any agent directly:
```
"Use code-security-reviewer to review src/"
"Use dependency-auditor to scan this project"
```

**Team assessment** — with agent teams enabled, the team lead dispatches specialists in parallel and consolidates findings into a single report:
```
"Run a full security assessment of this project"
```

The team lead scopes the target, dispatches relevant specialists (skipping those whose focus area isn't present), deduplicates findings, identifies cross-domain risk chains, and produces a unified report using `templates/report.md`.

> Agent teams requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. See [Claude Code docs](https://code.claude.com/docs/en/agent-teams) for setup. Individual agents work without this flag.

## Example Output

Running `"Review src/auth/ for security issues"` on a Node.js/Express codebase produces findings like this:

```
Security Code Review — src/auth/
Scope: Node.js/Express, server-side, processes user credentials
Findings: CRITICAL 1 | HIGH 2 | MEDIUM 1 | LOW 0
```

### [CRITICAL] SQL Injection in User Lookup

- **CWE**: [CWE-89](https://cwe.mitre.org/data/definitions/89.html)
- **OpenCRE**: [CRE-764-507](https://www.opencre.org/cre/764-507) — Injection Prevention
- **OWASP Ref**: A03:2021 Injection
- **Location**: `src/auth/login.js:42`
- **Impact**: Attacker can extract the entire users table, bypass authentication, or execute arbitrary SQL via crafted `id` parameter
- **Evidence**:
  ```js
  // src/auth/login.js:42
  const user = await db.query("SELECT * FROM users WHERE id=" + req.params.id);
  ```
- **Remediation**: Use parameterized queries:
  ```js
  const user = await db.query("SELECT * FROM users WHERE id = $1", [req.params.id]);
  ```
- **Confidence**: HIGH

> Every skill produces structured findings with severity, CWE, evidence, and remediation code.
> See [`examples/`](examples/) for complete sample assessment reports.

## Plays

### AI/Agent Security plays

The differentiator — security procedures purpose-built for the AI agent era. Bundled inside the `ai-security-skills` plugin.

| Play | What It Does |
|------|-------------|
| [agent-security-audit](plugins/ai-security-skills/plays/agent-security-audit.md) | Audit agent permissions, prompt injection surfaces, data exfiltration paths, guardrails |
| [agentic-ai-risk-assess](plugins/ai-security-skills/plays/agentic-ai-risk-assess.md) | Assess agentic AI applications against OWASP Top 10 for Agentic Applications 2026 |
| [ai-security-verification](plugins/ai-security-skills/plays/ai-security-verification.md) | Verify AI-driven applications against the OWASP AI Security Verification Standard (AISVS) |
| [llm-risk-assess](plugins/ai-security-skills/plays/llm-risk-assess.md) | Assess LLM applications against OWASP Top 10 for LLM Applications |
| [mcp-server-review](plugins/ai-security-skills/plays/mcp-server-review.md) | Review MCP server implementations for overpermissioning, injection, data exposure |
| [multi-agentic-threat-model](plugins/ai-security-skills/plays/multi-agentic-threat-model.md) | Threat-model multi-agent systems using the CSA MAESTRO 7-layer framework and OWASP Multi-Agentic System Guide v1.0 |
| [prompt-injection-testing](plugins/ai-security-skills/plays/prompt-injection-testing.md) | Test LLM apps against 18 attack techniques, 20 evasions, 13 intents |


### Code & Dependency Analysis plays

Immediate, practical value for any codebase. Bundled inside the `code-security-skills` plugin.

| Play | What It Does |
|------|-------------|
| [sca-audit](plugins/code-security-skills/plays/sca-audit.md) | Scan dependencies for known CVEs with reachability analysis |
| [code-review-security](plugins/code-security-skills/plays/code-review-security.md) | Systematic security code review mapped to OWASP Top 10 and ASVS |
| [secrets-scan](plugins/code-security-skills/plays/secrets-scan.md) | Detect hardcoded credentials, API keys, and tokens |
| [api-security-review](plugins/code-security-skills/plays/api-security-review.md) | Review APIs against OWASP API Security Top 10 |
| [owasp-top10-web-review](plugins/code-security-skills/plays/owasp-top10-web-review.md) | Web application review against OWASP Top 10 (2021) |
| [mobile-code-review](plugins/code-security-skills/plays/mobile-code-review.md) | Native Android/iOS source code review against OWASP MASVS v2.1.0 |
| [iac-security-review](plugins/code-security-skills/plays/iac-security-review.md) | Review Terraform, Kubernetes, CloudFormation against CIS benchmarks and cloud security best practices |
| [securability-engineering-review](plugins/code-security-skills/plays/securability-engineering-review.md) | Assess code against FIASSE v1.0.4/SSEM securable attributes: Maintainability, Trustworthiness, Reliability, and Transparency |

### Planned

- **Tier 2**: Threat modeling, ASVS verification, infrastructure hardening
- **Tier 3**: WSTG testing checklist, DAST orchestration, attack surface mapping
- **Tier 5**: SAMM maturity assessment, compliance mapping, aggregate reporting

## Architecture

Three-layer design — every layer lives inside the plugin source folder so the marketplace install bundles everything the skills need:

- **`plugins/<name>/agents/`** — Autonomous security specialists with focused system prompts, co-located inside each plugin. Each agent invokes one or more skills, operates in an isolated context, and produces structured reports. Can work solo or as a coordinated team.
- **`plugins/<name>/skills/`** — Self-contained `SKILL.md` files following the [Agent Skills spec](https://agentskills.io/specification). Distributed through `plugins/code-security-skills/` and `plugins/ai-security-skills/`, registered in the marketplace via `.claude-plugin/marketplace.json`. Each skill summarizes a procedure and references its corresponding play inside the same plugin.
- **`plugins/<name>/plays/`** — Full reference procedures with detailed checklists, tables, decision criteria, and examples. Skills reference these for comprehensive coverage.
- **`plugins/<name>/templates/`** and **`plugins/<name>/data/`** — Output templates (`finding.md`, `report.md`) and OWASP reference datasets (FIASSE v1.0.4, ASVS v5.0, secure-code prompts) that skills load at runtime.

Agents orchestrate, skills execute, and plays provide the full procedure. The
generic installer adapts that same authored source to each harness without
creating a second canonical content tree.

## OWASP Foundation

All plays reference OWASP standards and datasets:

- [OWASP Top 10](https://owasp.org/www-project-top-ten/) — Web application risks
- [OWASP API Security Top 10](https://owasp.org/API-Security/) — API-specific risks
- [OWASP Top 10 for LLM Applications](https://genai.owasp.org) — AI/LLM risks
- [OWASP Agentic Security Initiative](https://genai.owasp.org/initiatives/agentic-security-initiative/) — Autonomous-agent risks (Top 10 for Agentic Applications)
- [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) — Security verification requirements
- [OWASP MASVS](https://mas.owasp.org/MASVS/) — Mobile Application Security Verification Standard
- [OWASP AISVS](https://github.com/OWASP/AISVS) — AI Security Verification Standard
- [OWASP WSTG](https://owasp.org/www-project-web-security-testing-guide/) — Testing methodology
- [OWASP SAMM](https://owaspsamm.org) — Security program maturity model
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org) — Developer security guidance
- [OWASP FIASSE](https://owasp.org/www-project-fiasse) — Framework for Inherently Adaptive and Securable Engineering (v1.0.4)

## Related Projects

| Project | Relationship |
|---------|-------------|
| [OWASP Secure Agent Playbook](https://github.com/OWASP/secure-agent-playbook) | Canonical upstream for the security corpus. This fork adds generic harness installation while keeping upstream content recognizable. |
| [OWASP Agent Skills Project](https://github.com/eoftedal/owasp-agent-skills-project) | Proactive ASVS 5.0 guidance for AI coding agents — helps agents **write** secure code. We use their ASVS reference data in `plugins/code-security-skills/data/asvs/`. Complementary: they guide code generation, we find vulnerabilities in existing code. |
| [Securability Engineering](https://github.com/Securability-Engineering) | Securable code generation (OWASP FIASSE) and secure code requirements (ASVS) via spec file analysis and generation constraint (benchmarked and tuned) for various AI code generation tools. |
| [Arcanum PI Taxonomy](https://github.com/Arcanum-Sec/arc_pi_taxonomy) | Prompt injection attack classification by Jason Haddix. Our `prompt-injection-testing` play is built on this taxonomy. CC BY 4.0. |
| [OpenCRE](https://www.opencre.org) | Cross-standard requirement mappings (CWE, ASVS, WSTG, NIST 800-53). We use OpenCRE links in findings for multi-framework traceability. |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.
Portability-layer changes must also follow the
[Fork Contract](docs/FORK_CONTRACT.md); canonical security-content changes are
best proposed to the upstream project first.

New plays should:

- Solve one well-defined security task
- Include clear trigger conditions (when should this play run?)
- Follow a structured procedure with checkpoints
- Produce findings using the in-plugin `templates/finding.md` format
- Reference OWASP standards where applicable
- Prefer existing tools (semgrep, trivy, osv-scanner, trufflehog) over reimplementing detection
- Live inside the appropriate plugin's `plays/` folder so they ship with the marketplace install

## License

Licensed under [Creative Commons Attribution 4.0 International](LICENSE.md) (CC-BY-4.0). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for attribution of upstream OWASP project content.
