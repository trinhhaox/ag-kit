---
description: Parallel session conductor. Spawns multiple Claude Code sessions on isolated git worktrees for independent tasks.
---

# /conduct - Parallel Conductor

$ARGUMENTS

---

## Task

Orchestrate parallel Claude Code sessions from a plan or config file.

### Usage

```
/conduct conductor.yaml          # Start from config file
/conduct PLAN.md                 # Parse plan, auto-create config
/conduct --status                # Check session status
/conduct --stop                  # Stop all sessions
/conduct --cleanup               # Remove worktrees and branches
```

### Steps

1. **Parse input**
   - If YAML config: use directly
   - If plan file: extract independent tasks, create conductor.yaml

2. **Validate**
   - Ensure git repo is clean (no uncommitted changes)
   - Ensure base branch exists
   - Ensure no branch name conflicts

3. **Execute**
   ```bash
   python .agent/skills/parallel-conductor/scripts/conductor.py <config>
   ```

4. **Monitor**
   - Script polls every 60s and logs to /tmp/ag-conductor-status.json
   - Use `--status` to check progress

5. **After completion**
   - Review changes per branch: `git log main..<branch> --oneline`
   - Merge: `git merge --no-ff <branch>` for each
   - If available, run `/review-cross` on merged result
   - Cleanup: `--cleanup` to remove worktrees

### Prerequisites

- Git repository with clean working directory
- `claude` CLI available in PATH
- Optional: `pyyaml` for config parsing (`pip install pyyaml`)
