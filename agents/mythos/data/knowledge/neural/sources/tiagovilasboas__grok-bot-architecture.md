<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/banner-dark.svg">
  <img src="docs/assets/banner-light.svg" alt="Grok Bot Architecture — AI agent teams, skills, MCP and human approval" width="100%">
</picture>

# Grok Bot Architecture: AI Agent Teams, Skills, MCP & Human Approval

**A reference architecture for AI agent teams with scoped roles, typed handoffs, and human approval before privileged actions.**

[![CI](https://github.com/tiagovilasboas/grok-bot-architecture/actions/workflows/ci.yml/badge.svg)](https://github.com/tiagovilasboas/grok-bot-architecture/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/tiagovilasboas/grok-bot-architecture?style=flat-square)](https://github.com/tiagovilasboas/grok-bot-architecture/stargazers)
![MCP-native](https://img.shields.io/badge/MCP-native-7C5CFF?style=flat-square)
![zero dependencies](https://img.shields.io/badge/dependencies-zero-22D3EE?style=flat-square)
[![Sponsor](https://img.shields.io/badge/sponsor-♥-ea4aaa?style=flat-square&logo=githubsponsors)](https://github.com/sponsors/tiagovilasboas)

[Grok Bot quick path](#grok-bot-quick-path-start-in-10-minutes) · [Agnostic quick start](#agnostic-quick-start) · [Architecture](docs/architecture.md) · [FAQ](docs/grok-bot-faq.md) · [Contributing](CONTRIBUTING.md) · [Sponsor](#support-the-project)

</div>

An independent, MIT-licensed reference architecture for organizing **AI agent teams** with reusable **agent skills**, **MCP connectors**, and **human-in-the-loop (HITL) approval**. Start with a chief-of-staff and scoped specialists, then use typed handoffs and persisted approval requests to coordinate work across local and remote hosts.

Designed for engineers and operators structuring persistent AI teammates without granting unchecked ambient authority. The reference is model- and framework-independent; it is not affiliated with xAI or Cursor and does not contain the Grok Bot product's source code.

## How it works

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/flow-dark.svg">
  <img src="docs/assets/flow-light.svg" alt="Four steps: Goal (the human sets a goal), Coordinate (chief-of-staff assigns a scoped specialist), Execute (the specialist works with scoped tools and typed handoffs), Approve (a human decision bound to the action and revision)" width="100%">
</picture>
</div>

## Why this exists

<table>
<tr>
<td width="50%" valign="top"><strong>Scoped roles</strong><br>Nine role skills, each with its own job, context, deliverable and boundary. Roles describe responsibilities; the host enforces permissions.</td>
<td width="50%" valign="top"><strong>Typed handoffs</strong><br>Every handoff requires an owner, goal, completion condition and references, so work moves between roles with evidence instead of chat history.</td>
</tr>
<tr>
<td valign="top"><strong>Approval that fails closed</strong><br>A decision is bound to an exact action and revision. With no decision, execution waits (<code>default_on_timeout: wait</code>).</td>
<td valign="top"><strong>Zero-dependency validators</strong><br>No external packages, credentials or API keys. One command, <code>bash scripts/check.sh</code>, runs the validators and 31 runtime and board unit tests.</td>
</tr>
</table>

## Grok Bot quick path (start in 10 minutes)

To try this pattern on Grok Bot:

1. **Follow the 10-step setup:** Create your coordinator and specialist Bots with paste-ready hard rules, a budgeted routine example, and a first approval stop ([grok-bot/SETUP.md](grok-bot/SETUP.md)).
2. **Install skills & kickoffs:** Load the nine role skills via Cursor plugin or direct paste ([install guide](docs/hosts/grok-bot/install.md)) and use the full role kickoffs ([kickoff prompts](examples/grok-bot/kickoff/README.md)).
3. **Configure approval policy:** Map the four repository gates to personal Auto Review rules ([approval policy](docs/hosts/grok-bot/approval-policy.md)).
4. **Run the walkthrough & read the incident case study:** Follow an end-to-end task ([Grok Bot walkthrough](examples/grok-bot/walkthrough.md)) and see why routines require budgets and fail-closed stops ([sanitized case study](docs/case-study.md)).

*(See the [verification report](docs/hosts/grok-bot/verification-report.md) for what has been observed on a live Grok Bot account versus documented from official product facts).*

## Agnostic quick start

Validate contract fixtures and run the local reference approval lifecycle:

```bash
git clone https://github.com/tiagovilasboas/grok-bot-architecture.git
cd grok-bot-architecture
bash scripts/check.sh
```

No external packages, credentials, or API keys are required. The check exercises JSON validators, Markdown board validation, plugin packaging rules, documentation coherence, link checks, and 31 runtime and board unit tests.

Check individual handoff or interrupt records, or inspect and validate a Markdown board:

```bash
node scripts/validate-handoff.mjs /path/to/handoff.json
node scripts/validate-interrupt.mjs /path/to/interrupt.json
node scripts/board.mjs list --file examples/board.example.md
node scripts/board.mjs check --file examples/board.example.md
```

These checkers validate file shapes; they do not authenticate human approvers or execute side effects. Read the [agnostic walkthrough](examples/walkthrough.md) for a general task lifecycle or the [repository self-audit case study](examples/case-study-self-audit.md) for a real walkthrough backed by this repository's commit history.

## When this architecture helps

Use it when several jobs share infrastructure and their context, credentials, or write permissions need different boundaries: for example, inbox triage alongside engineering and publishing.

Start with a coordinator and one specialist. Add another role only when a concrete boundary justifies it. For one person working on one repository with one tool set, a single agent may be sufficient.

Use the [decision guide](docs/cookbook/when-to-use-this-pattern.md) before adding coordination.

## Architecture

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/architecture-dark.svg">
  <img src="docs/assets/architecture-light.svg" alt="Architecture diagram. The Human operator passes goals and constraints to the Chief-of-staff, which assigns work to the core team (Publishing, Security, Career, Inbox, Engineering) and the optional domain specialists (Finance, Product, Hobby). Below them, the vendor-independent host adapter holds Scoped tool access, an optional Isolated code worker, Shared state, Role skills, the Approval gate and MCP connectors / first-party APIs. Roles act through scoped tools; authorized reads and drafts go straight to connectors, while privileged action requests stop at the Approval gate, which asks the human and waits for an explicit decision before passing the approved action to the connectors. Engineering hands scoped implementation to the code worker, which returns branch and PR references to Shared state." width="100%">
</picture>
</div>

Chief-of-staff coordinates five other Core team roles and three optional Domain specialists. Each role loads its own skill and works through scoped host permissions. Shared state carries assignments and evidence; privileged actions require an authenticated decision bound to the action and revision. Isolated code workers return review artifacts through Engineering.

See [architecture and trust boundaries](docs/architecture.md) and the [host integration contract](docs/host-integration.md).

## Roles: jobs, deliverables, and boundaries

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/crew-dark.svg">
  <img src="docs/assets/crew-light.svg" alt="Meet the crew: six Core team roles (Chief-of-staff, Engineering, Publishing, Security, Inbox, Career) and three optional Domain specialists (Finance, Product, Hobby), each shown as a colored avatar with a one-line job" width="100%">
</picture>
</div>

Each role's head is also available as a [standalone SVG](docs/assets/crew/README.md) that you can reuse as an agent avatar.

My reference setup uses two groups: **Core team** (coordination and cross-cutting work) and optional **Domain specialists** (finance, product and hobby work). They are a menu to adapt, not a requirement to activate all nine agents.

| Role | Day-to-day job | Expected deliverable |
|---|---|---|
| **Chief-of-staff** | Turn goals into scoped assignments, prioritize the next increment, dispatch an owner, and review completion. | Assignment card, acceptance decision, blockers and concise next action. |
| **Engineering** | Implement scoped code and configuration changes, maintain CI, and package branches and pull requests for review. | Reviewable diff, required checks, implementation notes and residual risks. |
| **Publishing** | Improve public-facing READMEs, documentation, repository presentation, profiles and technical articles. | Source-backed draft or preview, checked links and clear publication status. |
| **Security** | Review application security and technical privacy within an explicitly authorized scope. | Evidence-backed findings with locations and remediation, or an explicit no-finding result. |
| **Inbox** | Review bounded batches of inbound messages and scheduling items, prioritize attention, and prepare drafts. | Digest, source references, proposed dispositions, replies and calendar proposals. |
| **Career** | Screen opportunities against supplied preferences, assess fit and prepare truthful tailored applications. | Ranked shortlist, requirement gaps, source links and application drafts. |
| **Finance** | Own finance-application requirements and reconcile authorized records into traceable drafts. | Requirements, reconciled totals, assumptions, discrepancy list and review references. |
| **Product** | Turn one application's user problems into prioritized increments, acceptance criteria and preview reviews. | Problem statement, scoped plan, implementation handoff and validation notes. |
| **Hobby** | Research discretionary interests, compare offers and explain value, availability and uncertainty. | Comparable shortlist with sources, dates, condition and total-price assumptions. |

Expand a role for its working contract. Full procedures live in the linked skill; the host enforces its actual permissions.

<details>
<summary><strong>Chief-of-staff</strong> — Core team coordinator</summary>

- **Job:** Turn goals into scoped assignments, prioritize the next increment, dispatch an owner, and review completion.
- **Required context:** User goal; existing authorization; constraints; board state; relevant specialist evidence.
- **Delivers:** Assignment card, acceptance decision, blockers and concise next action.
- **Boundary:** Do not become the default coder, publisher, or mailbox operator. Do not infer broad tool rights from the coordinator role.
- **Done when:** Every task has one owner; acceptance cites evidence; authority and outstanding blockers are explicit.

Example: “Choose the next documentation improvement and route it to the right specialist.”

[Load the Chief-of-staff skill](skills/chief-of-staff/SKILL.md).

</details>

<details>
<summary><strong>Engineering</strong> — Core team</summary>

- **Job:** Implement scoped code and configuration changes, maintain CI, and package branches and pull requests for review.
- **Required context:** Repository instructions; clean/dirty state; target behavior; authorized files and branch; acceptance criteria.
- **Delivers:** Reviewable diff, required checks, implementation notes and residual risks.
- **Boundary:** Commit as the actual contributor using repository policy. Do not force push, merge to default, tag, deploy, or change secrets without applicable authority. Bound external contr

<!-- truncated for Mythos neural library -->
