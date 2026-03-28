---
description: Launch persistent browser and navigate to URL. Provides interactive element refs for QA testing.
---

# /browse - Browser Automation

$ARGUMENTS

---

## Task

Start or reuse the persistent browser daemon and navigate to a URL.

### Usage

```
/browse https://example.com          # Navigate to URL
/browse --refs                       # Show current element refs
/browse --screenshot                 # Take screenshot
/browse --stop                       # Stop daemon
```

### Steps

1. **Check if daemon is running**
   - Check if `/tmp/ag-browser-token` exists
   - If not: start daemon in background
     ```bash
     python .agent/skills/browser-automation/scripts/browser-daemon.py &
     sleep 2  # Wait for startup
     ```

2. **Execute command**
   - If URL provided: `browser-cli.py navigate <url>`
   - If `--refs`: `browser-cli.py refs`
   - If `--screenshot`: `browser-cli.py screenshot`
   - If `--stop`: `browser-cli.py stop`

3. **Show results**
   - After navigate: show page title + element ref list
   - After screenshot: show the saved image path
   - Agent can now use refs to interact: click, type, etc.

### Prerequisites

```bash
pip install playwright && playwright install chromium
```
