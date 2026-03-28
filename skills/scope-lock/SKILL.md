---
name: scope-lock
description: Scope restriction for agent edits. Limits Write/Edit to specified paths only.
version: 1.0
---

# Scope Lock

Restricts file editing to a defined set of paths. When a freeze scope is active, all Write/Edit operations outside the allowed paths are blocked by the privacy-guard hook.

## How It Works

1. User runs `/freeze src/components/ src/lib/api.ts`
2. Allowed paths are written to `.agent/.freeze-scope` (one path per line)
3. `privacy-guard.sh` reads this file before every Edit/Write
4. If target file is outside all allowed paths → BLOCKED
5. User runs `/unfreeze` → scope file deleted, all edits allowed again

## Rules for Agents

- **ALWAYS** check if `.agent/.freeze-scope` exists before suggesting edits
- If scope is active, **ONLY** propose changes to files within the allowed paths
- If a necessary change is outside scope, inform the user and suggest `/unfreeze` first
- Never modify or delete `.agent/.freeze-scope` directly — use `/unfreeze`

## State File Format

`.agent/.freeze-scope`:
```
src/components/
src/lib/api.ts
```

Each line is either a directory (trailing `/`) or exact file path. A file matches if its path starts with any listed entry.
