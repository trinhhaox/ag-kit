# Conductor Config Reference

## Format

YAML file with `conductor` root key.

```yaml
conductor:
  base_branch: main                    # Branch to create worktrees from
  max_concurrent: 5                    # Max parallel sessions (default: 5)
  sessions:
    - name: session-name               # Unique identifier (alphanumeric + hyphens)
      task: "Description of work"      # Prompt for Claude Code session
      branch: feat/branch-name         # Git branch name for this session
      depends_on: other-session        # Optional: wait for this session first
```

## Fields

### `conductor`
- `base_branch` (required): Git branch to branch from
- `max_concurrent` (optional, default 5): Concurrency limit

### `sessions[]`
- `name` (required): Unique session ID. Used for worktree path and status tracking.
- `task` (required): The prompt/instruction for Claude Code. Be specific.
- `branch` (required): Git branch name. Created automatically. Must not exist.
- `depends_on` (optional): Name of another session that must complete first.

## Example: Full-Stack Feature

```yaml
conductor:
  base_branch: main
  sessions:
    - name: database
      task: "Create Prisma schema for User and Order models with migrations"
      branch: feat/db-schema

    - name: api
      task: "Implement REST API endpoints for /users and /orders using the Prisma models"
      branch: feat/api
      depends_on: database

    - name: ui
      task: "Build React components for user management dashboard"
      branch: feat/ui

    - name: tests
      task: "Write integration tests for User and Order API endpoints"
      branch: feat/tests
      depends_on: api
```

This creates 4 sessions: `database` and `ui` run in parallel, `api` waits for `database`, `tests` waits for `api`.

## Status File

Written to `/tmp/ag-conductor-status.json`:

```json
{
  "started_at": "2026-03-28T22:00:00Z",
  "config": "conductor.yaml",
  "sessions": [
    {
      "name": "database",
      "status": "completed",
      "branch": "feat/db-schema",
      "worktree": "/tmp/ag-wt-database",
      "pid": 12345,
      "started_at": "2026-03-28T22:00:01Z",
      "completed_at": "2026-03-28T22:05:30Z",
      "exit_code": 0
    }
  ]
}
```
