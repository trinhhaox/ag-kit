#!/usr/bin/env bash
set -euo pipefail

# Cross-AI Review Script
# Collects code reviews from Gemini CLI and/or Codex CLI
# Usage: cross-review.sh [gemini|codex|all]

AI_TARGET="${1:-all}"
OUTPUT_DIR="/tmp/ag-cross-review-$$"
mkdir -p "$OUTPUT_DIR"

# Get diff (staged + unstaged)
DIFF=$(git diff HEAD 2>/dev/null || git diff 2>/dev/null || echo "")

if [ -z "$DIFF" ]; then
  echo "No changes to review. Stage or commit changes first."
  exit 1
fi

# Read prompt template
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT_TEMPLATE="$SCRIPT_DIR/../references/review-prompt.md"

if [ -f "$PROMPT_TEMPLATE" ]; then
  PROMPT="You are reviewing a code diff. Analyze for:

1. **Bugs** — Logic errors, off-by-one, null/undefined access, race conditions
2. **Security** — Injection, XSS, CSRF, secrets exposure, insecure defaults
3. **Performance** — N+1 queries, unnecessary re-renders, memory leaks, large bundles
4. **Code Quality** — Dead code, unclear naming, missing error handling, DRY violations

Format each finding as:
- [SEVERITY: critical|high|medium|low] file:line — Description

Be specific. Reference exact lines. Skip obvious style issues.

--- DIFF START ---
$DIFF
--- DIFF END ---"
else
  PROMPT="Review this code diff for bugs, security issues, and code quality problems. Be specific with file:line references.

$DIFF"
fi

FOUND_AI=false

# Gemini CLI
if [[ "$AI_TARGET" == "gemini" || "$AI_TARGET" == "all" ]]; then
  if command -v gemini &>/dev/null; then
    echo "Collecting review from Gemini..." >&2
    echo "$PROMPT" | timeout 120 gemini > "$OUTPUT_DIR/gemini.txt" 2>/dev/null && FOUND_AI=true || echo "Gemini review failed or timed out" > "$OUTPUT_DIR/gemini.txt"
  else
    echo "Gemini CLI not found, skipping." >&2
  fi
fi

# Codex CLI
if [[ "$AI_TARGET" == "codex" || "$AI_TARGET" == "all" ]]; then
  if command -v codex &>/dev/null; then
    echo "Collecting review from Codex..." >&2
    timeout 120 codex -p "$PROMPT" > "$OUTPUT_DIR/codex.txt" 2>/dev/null && FOUND_AI=true || echo "Codex review failed or timed out" > "$OUTPUT_DIR/codex.txt"
  else
    echo "Codex CLI not found, skipping." >&2
  fi
fi

if [ "$FOUND_AI" = false ]; then
  echo "No AI tools available. Install gemini or codex CLI first."
  rm -rf "$OUTPUT_DIR"
  exit 1
fi

# Output collected reviews
echo "=== CROSS-AI REVIEW RESULTS ==="
echo ""
for f in "$OUTPUT_DIR"/*.txt; do
  [ -f "$f" ] || continue
  AI_NAME=$(basename "$f" .txt | tr '[:lower:]' '[:upper:]')
  echo "--- Review from $AI_NAME ---"
  cat "$f"
  echo ""
done

echo "Output directory: $OUTPUT_DIR"
echo "Synthesize these findings with your own review using the protocol in SKILL.md."
