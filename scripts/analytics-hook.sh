#!/usr/bin/env bash
# Analytics Hook - PostToolUse
# Logs tool/skill usage to the local SQLite database in one process.
python3 "$(dirname "$0")/analytics.py" hook 2>/dev/null
exit 0
