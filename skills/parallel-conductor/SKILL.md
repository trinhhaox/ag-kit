---
name: parallel-conductor
description: Multi-session orchestration. Spawns parallel Claude Code sessions on isolated git worktrees for independent tasks.
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
version: 1.0
priority: HIGH
---

# Parallel Conductor

Spawn multiple Claude Code sessions in parallel, each on an isolated git worktree, each executing an independent task from a plan.

## Runtime Script

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/conductor.py` | Session manager | `python scripts/conductor.py <config.yaml>` |
| `scripts/conductor.py --status` | Check status | `python scripts/conductor.py --status` |
| `scripts/conductor.py --stop` | Stop all sessions | `python scripts/conductor.py --stop` |

## Config Format

See `references/conductor-config.md` for full specification.

```yaml
conductor:
  base_branch: main
  sessions:
    - name: api-layer
      task: "Implement REST API endpoints"
      branch: feat/api
    - name: ui-components
      task: "Build dashboard React components"
      branch: feat/ui
```

## How It Works

1. **Parse** — Read config, validate tasks are independent
2. **Isolate** — Create git worktree per session: `git worktree add /tmp/ag-wt-{name} -b {branch}`
3. **Execute** — Spawn `claude -p "{task}" --cwd /tmp/ag-wt-{name}` for each
4. **Monitor** — Poll every 60s, track status in `/tmp/ag-conductor-status.json`
5. **Collect** — When all done, show summary of changes per session
6. **Merge** — Auto-merge non-conflicting branches; flag conflicts for human

## Rules

- Maximum 5 concurrent sessions (to avoid API rate limits)
- Each session gets its own worktree — complete isolation
- `depends_on` field allows sequencing when needed
- Failed sessions are logged but don't block others
- Always present merge summary before touching base branch
- Run `/review-cross` on merged result if available

## Merge Protocol

1. For each completed session: `git merge --no-ff {branch}` into base
2. If merge conflict: stop, show conflict files, ask user
3. After all merged: run tests on base branch
4. Clean up worktrees: `git worktree remove /tmp/ag-wt-{name}`
