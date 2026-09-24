# Scripts

Runtime scripts for AG Kit: agent hooks, validation runners, analytics and preview.
All scripts use only the Python standard library (PyYAML is optional).

## Hooks

| Script | Event | Behavior |
|--------|-------|----------|
| `privacy-guard.sh` → `privacy_guard.py` | PreToolUse | Exit `2` + reason on stderr blocks the tool call |
| `quality-gate.sh` → `quality_gate.py` | PostToolUse | Exit `2` + problems on stderr are shown to the agent (the edit is kept) |
| `analytics-hook.sh` → `analytics.py hook` | PostToolUse | Logs tool and skill usage; never fails |

The `.sh` files are thin wrappers so existing hook configs keep working.

### Privacy Guard

Blocks reads/writes/searches of `.env*` (except `.env.example|sample|template`), private keys
(`.pem`, `.key`, `.p12`, `.pfx`), SSH keys, `~/.aws/credentials`, `.netrc`, `.npmrc`,
`credentials.*`/`secrets.*` data files, and shell commands that print those files or
secret variables (`cat .env`, `source .env`, `echo $API_KEY`, ...). Source files such as
`credentials.ts` stay editable.

Scope lock: when `.agent/.freeze-scope` exists (created by `/freeze`), Edit/Write outside the
listed files/directories is blocked. Paths are resolved against the hook's `cwd` and matched on
directory boundaries (`src/auth/` does not unlock `src/authz/`).

### Quality Gate

| Extension | Check |
|-----------|-------|
| `.ts .tsx .mts .cts` | Local `node_modules/.bin/tsc --noEmit --incremental` (cache in `node_modules/.cache/ag-kit`), only errors of the edited file |
| `.json .jsonc` | JSON syntax; comments/trailing commas allowed in `tsconfig*.json`, `jsconfig*.json`, `.vscode/` |
| `.yml .yaml` | YAML syntax (if PyYAML installed) |
| `.py` | Python syntax (in-process) |
| `.sh .bash` | `bash -n` |
| `.prisma` | Local `prisma validate` |

Environment: `AG_QUALITY_GATE=block` (default) | `warn` (report, exit 0) | `off`.

## Validation runners

```bash
python3 scripts/checklist.py <project> [--url URL] [-j N] [--timeout S] [--json]
python3 scripts/verify_all.py <project> [--url URL] [--no-e2e] [--stop-on-fail] [-j N] [--json]
```

- Checks run in parallel (`-j`, default up to 4); output stays in priority order.
- `-j 1` runs sequentially; `checklist.py` then stops on the first critical failure.
- Check scripts are resolved from the kit itself, then `<project>/.agent/`.
- `--json` prints a machine-readable report on stdout (progress goes to stderr).
- Exit code `1` when any check fails.

Shared logic lives in `check_runner.py`.

## Analytics

```bash
python3 scripts/analytics.py stats --last 7d [--json]
python3 scripts/analytics.py top-tools --last 24h [--limit 10] [--json]
python3 scripts/analytics.py top-skills --last 30d [--json]
python3 scripts/analytics.py prune --older-than 90d
```

Data lives in `.data/analytics.db` (override with `AG_ANALYTICS_DB`). Skill usage is recorded
from `Skill` tool calls and reads of `skills/<name>/SKILL.md`.

## Preview & session

```bash
python3 scripts/auto_preview.py start [port] [--wait 30]   # uses pnpm/yarn/bun/npm based on lockfile
python3 scripts/auto_preview.py status [--json]            # real URL + health check
python3 scripts/auto_preview.py stop                       # stops the whole process group
python3 scripts/session_manager.py status [path]
```

## Tests

```bash
python3 -m unittest discover -s tests
```
