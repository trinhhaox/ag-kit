# AG Kit — Antigravity Agent Toolkit

A comprehensive AI agent capability expansion toolkit that turns Claude Code and Gemini CLI into a full engineering team. 20 specialist agents, 46 skills, 16 workflows — one install.

```
Think → Plan → Build → Review → Test → Ship
```

## Why AG Kit?

Instead of generic AI assistance, AG Kit provides **domain-specific agents** that understand their role. A security auditor thinks like a security auditor. A frontend specialist knows React patterns. A QA engineer tries to break your code.

**Progressive disclosure** — skills load on-demand based on your request. No context window bloat.

**Intelligent routing** — requests are automatically classified and routed to the right specialist agent.

**Quality hooks** — privacy guard blocks sensitive files, quality gate validates code after every edit.

## Quick Start

### Claude Code

```bash
# Clone
git clone https://github.com/trinhhaox/ag-kit.git ~/.antigravity/kit

# Symlink into your project
cd /path/to/your-project
ln -s ~/.antigravity/kit .agent

# Optional: Global slash commands
cp ~/.antigravity/kit/workflows/*.md ~/.claude/commands/
```

### Gemini CLI

```bash
# Clone
git clone https://github.com/trinhhaox/ag-kit.git ~/.antigravity/kit

# Symlink
cd /path/to/your-project
ln -s ~/.antigravity/kit .agent

# Copy MCP config (edit API keys as needed)
mkdir -p ~/.gemini/antigravity
cp ~/.antigravity/kit/mcp_config.json ~/.gemini/antigravity/mcp_config.json
```

### Hooks Setup (Claude Code)

Add to your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write|Bash|Glob",
        "hooks": [{
          "type": "command",
          "command": "bash .agent/scripts/privacy-guard.sh",
          "timeout": 5000
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "bash .agent/scripts/quality-gate.sh",
          "timeout": 30000
        }]
      }
    ]
  }
}
```

## What's Inside

### 20 Specialist Agents

| Agent | Domain |
|-------|--------|
| `orchestrator` | Multi-agent coordination, task delegation |
| `project-planner` | Task breakdown, dependency graphs, planning |
| `frontend-specialist` | React, Next.js, Tailwind, responsive design |
| `backend-specialist` | Node.js, Python, REST, serverless/edge |
| `database-architect` | Schema design, migrations, query optimization |
| `mobile-developer` | React Native, Flutter, cross-platform |
| `game-developer` | Unity, Godot, web/mobile/VR games |
| `devops-engineer` | CI/CD, Docker, deployment, infrastructure |
| `security-auditor` | OWASP 2025, supply chain, zero trust |
| `penetration-tester` | Red team, attack vectors, exploitation |
| `test-engineer` | TDD, Jest, Vitest, test strategies |
| `qa-automation-engineer` | Playwright, Cypress, E2E pipelines |
| `debugger` | Root cause analysis, systematic debugging |
| `performance-optimizer` | Core Web Vitals, bundle optimization |
| `seo-specialist` | E-E-A-T, SEO, Generative Engine Optimization |
| `documentation-writer` | API docs, guides, technical writing |
| `product-manager` | User stories, requirements, acceptance criteria |
| `product-owner` | Product vision, roadmap, backlog |
| `code-archaeologist` | Legacy code, refactoring, modernization |
| `explorer-agent` | Codebase discovery, architectural analysis |

### 46 Skills

<details>
<summary>Frontend & UI (6)</summary>

- **nextjs-react-expert** — React/Next.js performance optimization (Vercel Engineering patterns)
- **web-design-guidelines** — UI audit: accessibility, UX, performance (100+ rules)
- **tailwind-patterns** — Tailwind CSS v4 utilities and modern patterns
- **frontend-design** — Design systems, color theory, typography, UX psychology
- **mobile-design** — iOS/Android design patterns, touch psychology
- **game-development** — 2D/3D, multiplayer, VR/AR, web/mobile/PC games
</details>

<details>
<summary>Backend & API (4)</summary>

- **api-patterns** — REST vs GraphQL vs tRPC decision trees, response formats
- **nodejs-best-practices** — Async patterns, modules, event loop optimization
- **python-patterns** — FastAPI, async, type hints, project structure
- **rust-pro** — Rust 1.75+, async patterns, Tokio, axum
</details>

<details>
<summary>Database & Infrastructure (5)</summary>

- **database-design** — Schema design, normalization, indexing, ORM selection
- **deployment-procedures** — CI/CD, safe deployment, rollback strategies
- **server-management** — Process management, monitoring, scaling
- **caching-strategies** — Browser, CDN, Redis, app-level, invalidation
- **realtime-patterns** — WebSocket, SSE, pub/sub, connection management
</details>

<details>
<summary>Testing & Quality (5)</summary>

- **testing-patterns** — Unit, integration, mocking strategies
- **webapp-testing** — Playwright E2E, deep audit, browser testing
- **tdd-workflow** — RED-GREEN-REFACTOR cycle
- **code-review-checklist** — Code review standards and checklists
- **lint-and-validate** — Linting, type checking, static analysis
</details>

<details>
<summary>Security (3)</summary>

- **vulnerability-scanner** — OWASP 2025, supply chain security audit
- **red-team-tactics** — MITRE ATT&CK, attack phases, exploitation
- **authentication** — JWT, OAuth 2.0, passkeys, RBAC, MFA patterns
</details>

<details>
<summary>Architecture & Planning (4)</summary>

- **architecture** — System design patterns, ADR documentation
- **app-builder** — Full-stack scaffolding with 13 project templates
- **plan-writing** — Task planning, breakdown, dependency graphs
- **brainstorming** — Socratic questioning, discovery methodology
</details>

<details>
<summary>AI & Context Engineering (4)</summary>

- **ai-patterns** — Agent architecture, prompt engineering, function calling
- **context-engineering** — Context window optimization, RAG patterns
- **intelligent-routing** — Request classification, agent selection
- **mcp-builder** — Model Context Protocol server building
</details>

<details>
<summary>gstack-Inspired (4) — NEW</summary>

- **scope-lock** — Restrict agent edits to specified paths (`/freeze` & `/unfreeze`)
- **cross-ai-review** — Multi-AI code review (Gemini + Codex synthesis)
- **browser-automation** — Persistent Playwright daemon, element ref system
- **parallel-conductor** — Multi-session orchestration on git worktrees
</details>

<details>
<summary>Other (11)</summary>

- **clean-code** — Pragmatic coding standards (global, always-on)
- **behavioral-modes** — Agent operational modes
- **parallel-agents** — Multi-agent orchestration patterns
- **seo-fundamentals** — SEO, E-E-A-T, Core Web Vitals
- **geo-fundamentals** — Generative Engine Optimization
- **i18n-localization** — Internationalization, RTL support
- **documentation-templates** — README, API docs, templates
- **systematic-debugging** — 4-phase debugging methodology
- **performance-profiling** — Web Vitals, bundle analysis
- **bash-linux** — Shell scripting, critical commands
- **powershell-windows** — PowerShell patterns, pitfalls
</details>

### 16 Slash Commands

| Command | What It Does |
|---------|-------------|
| `/plan` | Create implementation plan (no code) |
| `/create` | Build new application from scratch |
| `/enhance` | Add features to existing code |
| `/debug` | Systematic problem investigation |
| `/test` | Generate and run tests |
| `/deploy` | Production deployment with pre-flight checks |
| `/orchestrate` | Coordinate multiple agents for complex tasks |
| `/brainstorm` | Explore ideas before implementation |
| `/preview` | Local dev server management |
| `/status` | Project and agent status board |
| `/ui-ux-pro-max` | Advanced UI design with 50 styles |
| `/freeze` | Lock editing scope to specified paths |
| `/unfreeze` | Remove scope restriction |
| `/browse` | Launch persistent browser for QA |
| `/review-cross` | Multi-AI code review (Gemini + Codex) |
| `/conduct` | Parallel sessions on isolated worktrees |

## Features Inspired by gstack

Four capabilities adapted from [garrytan/gstack](https://github.com/garrytan/gstack), built from scratch for the AG Kit architecture:

### Scope Lock (`/freeze` & `/unfreeze`)

Restrict agent Write/Edit to specified paths only. Prevents accidental changes outside your task scope.

```
/freeze src/components/auth/     # Only allow edits here
/freeze src/lib/ src/utils/      # Multiple paths
/unfreeze                        # Remove restriction
```

Integrated into the privacy-guard hook — attempts to edit outside scope are blocked automatically.

### Cross-AI Review (`/review-cross`)

Get independent code reviews from Gemini CLI and Codex CLI, then synthesize findings.

```
/review-cross              # All available AIs
/review-cross --ai gemini  # Gemini only
/review-cross --ai codex   # Codex only
```

Each finding is classified: `[AGREE]`, `[DISAGREE]`, or `[NEW]` — reducing single-model blind spots.

### Browser Daemon (`/browse`)

Persistent Playwright browser with element ref system. Sub-200ms command latency via HTTP.

```
/browse https://example.com   # Navigate
/browse --refs                # List interactive elements (@e1, @e2...)
/browse --screenshot          # Capture page
/browse --stop                # Shutdown daemon
```

Elements addressed by refs (`@e1: button "Sign In"`) instead of fragile CSS selectors. Built from accessibility tree — works with Shadow DOM, CSP, and framework hydration.

**Requires:** `pip install playwright && playwright install chromium`

### Parallel Conductor (`/conduct`)

Spawn multiple Claude Code sessions on isolated git worktrees.

```yaml
# conductor.yaml
conductor:
  base_branch: main
  sessions:
    - name: api
      task: "Implement REST API endpoints"
      branch: feat/api
    - name: ui
      task: "Build dashboard components"
      branch: feat/ui
    - name: tests
      task: "Write integration tests"
      branch: feat/tests
      depends_on: api
```

```
/conduct conductor.yaml   # Start parallel sessions
/conduct --status         # Check progress
/conduct --cleanup        # Remove worktrees
```

## Architecture

```
.agent/
├── agents/          # 20 specialist agents (.md with frontmatter)
├── skills/          # 46 domain skills (SKILL.md + scripts/ + references/)
├── workflows/       # 16 slash commands (.md with $ARGUMENTS)
├── rules/           # 3 global rules (routing, checklist, behavior)
├── scripts/         # 8 scripts (hooks + validation + analytics)
└── mcp_config.json  # MCP server configuration
```

### How It Works

```
User Request
    ↓
Request Classifier (ROUTING_RULES.md)
    ↓
Agent Selection (intelligent-routing)
    ↓
Skill Loading (progressive disclosure — only relevant sections)
    ↓
Execution + Hooks (privacy-guard → work → quality-gate)
    ↓
Validation (checklist.py / verify_all.py)
```

### Three-Tier System

| Tier | Always Loaded | Content |
|------|--------------|---------|
| **0** | Yes | Global rules (clean-code, routing, checklist) |
| **1** | Per agent | Agent persona + skills from frontmatter |
| **2** | On demand | Specific skill sections based on request |

### Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `privacy-guard.sh` | Before Read/Edit/Write/Bash | Block sensitive files (.env, .pem, credentials) + scope lock |
| `quality-gate.sh` | After Edit/Write | Validate TypeScript, JSON, shell syntax, Prisma, Python |
| `analytics-hook.sh` | After any tool | Track usage metrics (local only) |

### Validation Scripts

```bash
# Quick validation (during development)
python .agent/scripts/checklist.py .

# Full verification (before deploy)
python .agent/scripts/verify_all.py . --url http://localhost:3000
```

Priority order: Security → Lint → Schema → Tests → UX → SEO → Lighthouse → E2E

## Per-Project Customization

Override or extend for specific projects:

```bash
# Create project-local overrides
mkdir -p .agent-custom/agents
mkdir -p .agent-custom/skills

# Add project-specific agent
echo "---
name: my-custom-agent
description: Handles project-specific tasks
tools: Read, Write, Edit, Bash
skills: clean-code, api-patterns
---
# Custom Agent Instructions
..." > .agent-custom/agents/custom.md
```

## Supported Platforms

| Platform | Support |
|----------|---------|
| Claude Code | Full (agents, skills, workflows, hooks) |
| Gemini CLI | Full (via GEMINI.md rules + MCP config) |
| Cursor | Partial (skills as context, no hooks) |
| Other AI IDEs | Skills readable as markdown documentation |

## Requirements

- **Claude Code** or **Gemini CLI** installed
- **Python 3.8+** (for validation scripts)
- **Git** (for parallel conductor worktrees)
- **Playwright** (optional, for browser daemon): `pip install playwright && playwright install chromium`
- **Gemini CLI / Codex CLI** (optional, for cross-AI review)

## License

MIT

## Credits

Four features inspired by [gstack](https://github.com/garrytan/gstack) by Garry Tan — built from scratch for the AG Kit architecture.
