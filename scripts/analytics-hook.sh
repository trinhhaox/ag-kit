#!/usr/bin/env bash
set -euo pipefail

# Analytics Hook - PostToolUse
# Logs tool usage to local SQLite database
# Reads JSON from stdin with tool_name and tool_input

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT=$(cat)

TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "unknown")
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

python3 "$SCRIPT_DIR/analytics.py" log \
  --event "tool_used" \
  --data "{\"tool\":\"$TOOL_NAME\"}" \
  --session "$SESSION_ID" 2>/dev/null || true

exit 0
