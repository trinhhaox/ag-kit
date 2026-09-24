#!/usr/bin/env bash
# Quality Gate - PostToolUse Hook
# Thin wrapper kept for backward-compatible hook configs; logic lives in
# quality_gate.py.
exec python3 "$(dirname "$0")/quality_gate.py"
