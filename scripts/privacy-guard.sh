#!/usr/bin/env bash
# Privacy Guard - PreToolUse Hook
# Thin wrapper kept for backward-compatible hook configs; logic lives in
# privacy_guard.py (single process, ~10x faster than the old per-pattern greps).
exec python3 -S "$(dirname "$0")/privacy_guard.py"
