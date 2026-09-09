# Copilot Autopilot

A template repository for **AI-driven autonomous product development** using VS Code Copilot agents.

## What is this?

A squad of specialized Copilot agents that collaborate through a structured
lifecycle to take a product from **vision** to **working software** —
autonomously.

## Development Lifecycle

The method has **six stages exposed through five entrypoints**. The canonical
stage order, gates, authorities, artefact ownership, and lock rules are owned
only by the
[`the-copilot-build-method`](.github/skills/the-copilot-build-method/SKILL.md)
skill; this table is a reader-oriented summary.

<!-- lifecycle-summary:start -->
| Stage | Entrypoint | Outcome |
|---|---|---|
| Vision sketch | `kickstart` | A VP sketch records the product intent. |
| Discovery | `discover` | A human accepts a `READY` or `READY_WITH_DEFERRALS` dossier verdict. |
| PRD finalization | `requirements` | A human approves measurable product requirements. |
| Architecture | `plan` stage 1 | A human accepts architecture derived from accepted Discovery and an approved PRD. |
| Planning | `plan` stage 2 | The product owner and validator admit delivery plans. |
| Autopilot | `autopilot` | The squad implements, tests, reviews, and completes the applicable Definition of Done. |
<!-- lifecycle-summary:end -->

## Quick Start

1. **Sketch the product vision with `kickstart`**
   - Run the `kickstart` skill in Copilot Chat
   - Brainstorm freely — capture ideas in `docs/vision_of_product/VP1-mvp/`
   - Add more VP scopes: `VP2-<feature>/`, `VP3-<feature>/`, etc.

2. **Run evidence-backed Discovery with `discover`**
   - Classify the scope and build `docs/discovery/VP<n>-<slug>/`
   - Obtain the human-accepted Discovery readiness verdict

3. **Finalize requirements with `requirements`**
   - Translate accepted Discovery into
     `docs/requirements/VP<n>-<slug>/PRD.md`
   - Obtain human PRD approval

4. **Create architecture and delivery plans with `plan`**
   - Stage 1 produces `docs/architecture/` and `docs/ADRs/`, then stops for
     human architecture acceptance
   - Stage 2 creates themes, executable epic specifications, optional stories,
     issue templates, and the backlog
     only after the architecture gate opens

5. **Launch delivery with `autopilot`**
   - Run the `autopilot` skill in Copilot Chat in "Autopilot" mode
   - One owner executes each bounded epic locally: implement → test → quality assessment
   - Session state persists in `docs/plan/backlog.yaml` — resume anytime

## Recommended MCP & CLI Tools

The agent squad uses a set of MCP servers and CLI tools. Configure them once for all agents to work optimally.

### Required for all modes

| Tool | Purpose | Setup |
|------|---------|-------|
| **GitHub MCP** | PRs, CI checks, code search, issue management | Built-in with VS Code Copilot; or add to `.vscode/mcp.json`: `{"mcpServers":{"github":{"type":"http","url":"https://api.githubcopilot.com/mcp/"}}}` |
| **Graphify CLI** | Local codebase graph queries when `graphify-out/graph.json` exists | Install/initialize Graphify separately, then agents use `graphify query "<question>" --graph "$REPO/graphify-out/graph.json"` before broad text search |
| **git CLI** | Commits, diffs, file history | Pre-installed on most systems — `git --version` to verify |
| **gh CLI** | CI log retrieval, issue/PR management | [cli.github.com](https://cli.github.com) — run `gh auth login` after install |

### Required for UI projects (developer agent)

| Tool | Purpose | Setup |
|------|---------|-------|
| **Playwright MCP** | Browser automation for end-to-end UI tests | Add to `.vscode/mcp.json`: `{"mcpServers":{"playwright":{"type":"stdio","command":"npx","args":["@playwright/mcp@latest"]}}}` |

> See [`.github/agents/README.md`](.github/agents/README.md) for the full per-agent tool matrix, and the `the-copilot-build-method` skill for MCP server configuration snippets.

## Agent Squad

| Agent | Role | Lifecycle responsibility |
|-------|------|-------|
| **discovery-facilitator** | Maintains a coherent dossier without taking human authority | Discovery |
| **investigator** | Returns evidence for one bounded Discovery question | Discovery |
| **requirements-facilitator** | Drafts measurable, traceable requirements | PRD finalization |
| **architect** | Produces architecture, tech stack, and ADRs | Architecture |
| **product-owner** | Produces themes, executable epics, optional BDD stories, and planning admission | Planning |
| **orchestrator** | Sequences delivery and manages runtime state | Autopilot |
| **developer** | Owns one bounded epic through implementation, testing, and local repair | Autopilot |
| **reviewer** | Provides independent epic review when required; native review may fulfil this role | Autopilot |
| **troubleshooter** | Diagnoses unresolved epic failures after bounded owner repair | Autopilot |

## Directory Structure

```
docs/
├── vision_of_product/    # Free-form product vision
├── discovery/            # Evidence, decisions, risks, and readiness
├── requirements/         # Approved PRDs and change records
├── architecture/         # System design + tech stack
├── ADRs/                 # Architecture Decision Records
├── themes/               # TH<n>/epics/E<m>/README.md + optional stories/
└── plan/
    ├── backlog.yaml      # Runtime state (active themes + archive index)
    ├── backlog-archive/  # Completed theme snapshots (TH<n>.yaml)
    └── session-log.md    # Autopilot session history

.github/
├── agents/               # Specialized agent definitions
├── prompts/              # Optional prompts (for example /review, /troubleshoot)
├── skills/               # Reusable skills (kickstart, discover, requirements,
│                         #   plan, autopilot,
│                         #   the-copilot-build-method,
│                         #   bdd-stories, backlog-management, code-quality,
│                         #   architecture-decisions)
├── ISSUE_TEMPLATE/       # One issue template per epic (generated by plan skill)
│   └── archive/          # Completed-theme templates (moved here at theme boundary)
├── hooks/                # Session lifecycle automation
└── copilot-instructions.md
```

## Key Conventions

- **VP<n> ↔ TH<n>**: Vision phases map 1:N to implementation themes
- **Epic-first execution**: One bounded epic per developer assignment; optional
  stories are acceptance slices, not separate agent jobs
- **Backlog is truth**: `docs/plan/backlog.yaml` is the runtime source the orchestrator trusts
- **Behavioral acceptance**: Epic specifications own measurable criteria and
  relevant examples; Given/When/Then is used where it clarifies behavior
- **Language-agnostic**: Architect agent chooses tech stack based on your vision

## Epic-First Delivery

New themes use `schema-version: 3` from `backlog-management`. Each epic has an
executable specification at
`docs/themes/TH<n>-<slug>/epics/E<m>-<slug>/README.md`; an epic with no stories
is valid. The `bdd-stories` skill owns this format and optional child stories.
Split work when the outcome cannot be safely implemented and reviewed as one
bounded change, not merely because it contains several technical tasks.

`method packet project` selects the next eligible delivery unit.
`method packet build --epic TH<n>.E<m>` grants exactly that epic, including
declared child acceptance scope. The owner performs implementation,
integration checks, and local repairs in context. Verification, quality
assessment, and Gitflow evidence are recorded at epic scope, without
per-story review or merge-request cycles. Required independent review can use
the native review capability instead of an additional custom-agent pass.

Existing version 1/2 themes and `--story` packets retain their legacy behavior.
Accepted history is not migrated; a story packet never implicitly authorizes
an entire epic. See the canonical method for risk-based review, recovery,
completion, and human acceptance rules.

The accepted VP3 architecture and ADRs remain unchanged as the historical
baseline. The prospective epic-first delivery contract is owned by the updated
`the-copilot-build-method`, `backlog-management`, and `bdd-stories` skills.

For an admitted v3 theme, build its projected epic packet with:

```bash
bin/method packet build --task implement-epic --epic TH4.E1 --mode developer \
  --implementation-root /work/implementation/checkout \
  --allowed-implementation-root /work/implementation \
  --planning-root /work/authoritative-repository
```

Retain the returned `authorization_hash` outside the packet and use it with
`packet preflight`, `reconcile`, and `verify` as described by `autopilot`.
The implementation checkout and authoritative planning repository must be
disjoint.

## Using as a Template

### From GitHub (recommended)

```bash
gh repo create my-product --template guillaume-galp/copilotautopilot --public --clone && cd my-product
```

### Without GitHub CLI

```bash
git clone --depth 1 https://github.com/guillaume-galp/copilotautopilot.git my-product \
  && cd my-product && rm -rf .git && git init && git add . \
  && git commit -m "Initial commit from copilotautopilot template"
```

Then open the folder in VS Code and run the `kickstart` skill in Copilot Chat to start designing your product.

## License

MIT
