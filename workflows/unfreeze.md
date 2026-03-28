---
description: Remove editing scope restriction set by /freeze. Allows agent to edit any file.
---

# /unfreeze - Remove Scope Lock

---

## Task

Remove the current scope restriction.

### Steps

1. Check if `.agent/.freeze-scope` exists
2. If exists: delete it, confirm "Scope restriction removed. All files are now editable."
3. If not exists: inform "No scope restriction is currently active."

### Implementation

```bash
SCOPE_FILE=".agent/.freeze-scope"
if [ -f "$SCOPE_FILE" ]; then
  rm "$SCOPE_FILE"
  echo "Scope restriction removed. All files are now editable."
else
  echo "No scope restriction is currently active."
fi
```
