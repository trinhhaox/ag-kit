---
name: browser-automation
description: Persistent Playwright browser daemon for QA testing, web interaction, and screenshots. Sub-200ms command latency via HTTP API.
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
version: 1.0
priority: HIGH
---

# Browser Automation

Persistent Playwright browser daemon with element ref system for fast, reliable web interaction.

## Runtime Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/browser-daemon.py` | Start browser server | `python scripts/browser-daemon.py [--port 9222]` |
| `scripts/browser-cli.py` | Send commands to daemon | `python scripts/browser-cli.py <command> [args...]` |

**Requires:** `pip install playwright && playwright install chromium`

## Quick Start

```bash
# Start daemon (runs in background)
python .agent/skills/browser-automation/scripts/browser-daemon.py &

# Navigate
python .agent/skills/browser-automation/scripts/browser-cli.py navigate https://example.com

# List elements
python .agent/skills/browser-automation/scripts/browser-cli.py refs

# Click element
python .agent/skills/browser-automation/scripts/browser-cli.py click @e1

# Type text
python .agent/skills/browser-automation/scripts/browser-cli.py type @e2 "hello@example.com"

# Screenshot
python .agent/skills/browser-automation/scripts/browser-cli.py screenshot

# Stop daemon
python .agent/skills/browser-automation/scripts/browser-cli.py stop
```

## API Endpoints

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | /navigate | `{"url": "..."}` | `{"title": "...", "url": "..."}` |
| POST | /click | `{"ref": "@e1"}` | `{"ok": true}` |
| POST | /type | `{"ref": "@e2", "text": "..."}` | `{"ok": true}` |
| POST | /screenshot | `{"full_page": false}` | `{"image": "base64..."}` |
| POST | /evaluate | `{"script": "document.title"}` | `{"result": "..."}` |
| POST | /wait | `{"ref": "@e1", "timeout": 5000}` | `{"ok": true}` |
| GET | /refs | — | `{"refs": {"@e1": {...}, ...}}` |
| GET | /status | — | `{"url": "...", "title": "...", "refs_count": N}` |
| POST | /stop | — | Graceful shutdown |

## Ref System

Elements are addressed by refs (`@e1`, `@e2`, ...) built from the accessibility tree. See `references/ref-system.md` for details.

**Key rules:**
- Refs auto-clear on navigation
- Refs rebuild after each command that changes the page
- Use `refs` command to see current mapping
- Refs use Playwright locators internally — no CSS selectors needed

## Security

- Localhost-only binding (127.0.0.1)
- UUID bearer token per session (stored in /tmp/ag-browser-token)
- 30 min idle auto-shutdown
