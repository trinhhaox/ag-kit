#!/usr/bin/env bash
set -euo pipefail

# Quality Gate - PostToolUse Hook
# Validates files after Edit/Write operations
# Reads JSON from stdin with tool_name and tool_input/tool_result

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
TOOL_INPUT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('tool_input',{})))" 2>/dev/null || echo "{}")

# Extract file path from tool input
FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path', d.get('path','')))" 2>/dev/null || echo "")

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

# Skip directories that don't need checking
SKIP_PATTERNS=("node_modules" ".next" "dist" "build" ".git" "__pycache__" ".turbo" "coverage")
for pattern in "${SKIP_PATTERNS[@]}"; do
  if echo "$FILE_PATH" | grep -q "$pattern"; then
    exit 0
  fi
done

EXTENSION="${FILE_PATH##*.}"
BASENAME=$(basename "$FILE_PATH")
WARNINGS=""

# Find the nearest project root (directory with package.json or tsconfig.json)
find_project_root() {
  local dir="$1"
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/tsconfig.json" ] || [ -f "$dir/package.json" ]; then
      echo "$dir"
      return
    fi
    dir=$(dirname "$dir")
  done
  echo ""
}

case "$EXTENSION" in
  ts|tsx)
    PROJECT_ROOT=$(find_project_root "$(dirname "$FILE_PATH")")
    if [ -n "$PROJECT_ROOT" ] && [ -f "$PROJECT_ROOT/tsconfig.json" ]; then
      TSC_OUTPUT=$(cd "$PROJECT_ROOT" && npx tsc --noEmit --pretty false 2>&1 | head -20) || true
      if [ -n "$TSC_OUTPUT" ]; then
        # Filter to only show errors related to the edited file
        FILE_ERRORS=$(echo "$TSC_OUTPUT" | grep -F "$(basename "$FILE_PATH")" | head -5) || true
        if [ -n "$FILE_ERRORS" ]; then
          WARNINGS="TypeScript errors in $(basename "$FILE_PATH"):\n$FILE_ERRORS"
        fi
      fi
    fi
    ;;
  json)
    if [ "$BASENAME" != "package-lock.json" ]; then
      JSON_CHECK=$(python3 -m json.tool "$FILE_PATH" > /dev/null 2>&1) || WARNINGS="Invalid JSON syntax in $BASENAME"
    fi
    ;;
  sh|bash)
    BASH_CHECK=$(bash -n "$FILE_PATH" 2>&1) || WARNINGS="Shell syntax error in $BASENAME:\n$BASH_CHECK"
    ;;
  prisma)
    PROJECT_ROOT=$(find_project_root "$(dirname "$FILE_PATH")")
    if [ -n "$PROJECT_ROOT" ] && command -v npx &>/dev/null; then
      PRISMA_CHECK=$(cd "$PROJECT_ROOT" && npx prisma validate 2>&1) || WARNINGS="Prisma validation error:\n$PRISMA_CHECK"
    fi
    ;;
  py)
    PY_CHECK=$(python3 -c "import py_compile; py_compile.compile('$FILE_PATH', doraise=True)" 2>&1) || WARNINGS="Python syntax error in $BASENAME:\n$PY_CHECK"
    ;;
esac

if [ -n "$WARNINGS" ]; then
  echo -e "⚠️  Quality Gate: $WARNINGS"
fi

# Always exit 0 - quality gates warn but don't block
exit 0
