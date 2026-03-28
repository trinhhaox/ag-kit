---
description: Lock editing scope to specified file/directory paths. Prevents accidental changes outside task scope.
---

# /freeze - Scope Lock

$ARGUMENTS

---

## Task

Lock the agent's editing scope to the specified paths only.

### Usage

```
/freeze src/components/auth/          # Single directory
/freeze src/lib/api.ts                # Single file
/freeze src/components/ src/lib/      # Multiple paths
```

### Steps

1. **Validate arguments**
   - At least one path argument is required
   - Each path must exist (file or directory)
   - If a path doesn't exist, warn and skip it

2. **Write scope file**
   - Write validated paths to `.agent/.freeze-scope` (one per line)
   - If file already exists, overwrite it (new freeze replaces old)
   - Directories should have trailing `/`

3. **Confirm to user**
   - List all locked paths
   - Remind: "Use /unfreeze to remove scope restriction"

### Implementation

```bash
SCOPE_FILE=".agent/.freeze-scope"
> "$SCOPE_FILE"  # Clear/create

for path in $ARGUMENTS; do
  if [ -e "$path" ]; then
    if [ -d "$path" ]; then
      echo "${path%/}/" >> "$SCOPE_FILE"
    else
      echo "$path" >> "$SCOPE_FILE"
    fi
  else
    echo "WARNING: Path '$path' does not exist, skipping"
  fi
done

echo "Scope locked to:"
cat "$SCOPE_FILE"
echo ""
echo "Use /unfreeze to remove restriction."
```
