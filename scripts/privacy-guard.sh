#!/usr/bin/env bash
set -euo pipefail

# Privacy Guard - PreToolUse Hook
# Blocks access to sensitive files (.env, .pem, credentials, etc.)
# Reads JSON from stdin with tool_name and tool_input

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
TOOL_INPUT=$(echo "$INPUT" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('tool_input',{})))" 2>/dev/null || echo "{}")

# Sensitive file patterns (regex)
SENSITIVE_PATTERNS=(
  '\.env$'
  '\.env\.'
  '\.pem$'
  '\.key$'
  '\.p12$'
  '\.pfx$'
  'credentials'
  'secrets'
  'id_rsa'
  'id_ed25519'
  '\.cloudflared/.*\.json$'
  '\.cloudflared/cert\.pem'
)

# Allowed exceptions
ALLOWED_PATTERNS=(
  '\.env\.example'
  '\.env\.sample'
  '\.env\.template'
  'node_modules'
)

check_path() {
  local filepath="$1"

  # Check allowed exceptions first
  for allowed in "${ALLOWED_PATTERNS[@]}"; do
    if echo "$filepath" | grep -qE "$allowed"; then
      return 0
    fi
  done

  # Check sensitive patterns
  for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if echo "$filepath" | grep -qiE "$pattern"; then
      echo "{\"decision\":\"block\",\"reason\":\"Privacy Guard: blocked access to sensitive file matching pattern '$pattern'. File: $filepath\"}"
      exit 2
    fi
  done

  return 0
}

check_bash_command() {
  local cmd="$1"

  # Sensitive env vars and commands
  local dangerous_patterns=(
    'cat\s+[^\|]*\.env'
    'cat\s+[^\|]*\.pem'
    'cat\s+[^\|]*\.key'
    'cat\s+[^\|]*credentials'
    'cat\s+[^\|]*secrets'
    'cat\s+[^\|]*id_rsa'
    'echo\s+\$DATABASE_URL'
    'echo\s+\$SECRET'
    'echo\s+\$API_KEY'
    'echo\s+\$PRIVATE_KEY'
    'printenv\s+(DATABASE_URL|SECRET|API_KEY|PRIVATE_KEY|JWT_SECRET)'
    'cat\s+[^\|]*\.cloudflared/'
  )

  for pattern in "${dangerous_patterns[@]}"; do
    if echo "$cmd" | grep -qiE "$pattern"; then
      echo "{\"decision\":\"block\",\"reason\":\"Privacy Guard: blocked command accessing sensitive data. Pattern: '$pattern'\"}"
      exit 2
    fi
  done

  return 0
}

check_freeze_scope() {
  local filepath="$1"
  local project_root
  project_root=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

  if [ -z "$project_root" ]; then
    # Not a git repo, try to find .agent relative to script
    local script_dir
    script_dir="$(cd "$(dirname "$0")" && pwd)"
    project_root="$(dirname "$(dirname "$script_dir")")"
  fi

  local scope_file="$project_root/.agent/.freeze-scope"
  if [ ! -f "$scope_file" ]; then
    return 0
  fi

  while IFS= read -r scope; do
    [ -z "$scope" ] && continue
    local abs_scope="$project_root/$scope"
    if [[ "$filepath" == "$abs_scope"* ]]; then
      return 0
    fi
  done < "$scope_file"

  echo "{\"decision\":\"block\",\"reason\":\"Scope Lock: file '$filepath' is outside frozen scope. Run /unfreeze to remove restriction.\"}"
  exit 2
}

case "$TOOL_NAME" in
  Read)
    FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path', d.get('path','')))" 2>/dev/null || echo "")
    if [ -n "$FILE_PATH" ]; then
      check_path "$FILE_PATH"
    fi
    ;;
  Edit|Write)
    FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path', d.get('path','')))" 2>/dev/null || echo "")
    if [ -n "$FILE_PATH" ]; then
      check_path "$FILE_PATH"
      check_freeze_scope "$FILE_PATH"
    fi
    ;;
  Bash)
    COMMAND=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null || echo "")
    if [ -n "$COMMAND" ]; then
      check_bash_command "$COMMAND"
    fi
    ;;
  Glob)
    GLOB_PATTERN=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pattern',''))" 2>/dev/null || echo "")
    GLOB_PATH=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('path',''))" 2>/dev/null || echo "")
    if [ -n "$GLOB_PATTERN" ]; then
      check_path "$GLOB_PATTERN"
    fi
    if [ -n "$GLOB_PATH" ]; then
      check_path "$GLOB_PATH"
    fi
    ;;
esac

exit 0
