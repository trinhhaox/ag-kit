# Cross-AI Review Prompt Template

This prompt is sent to each external AI tool for code review.

## Template

```
You are reviewing a code diff. Analyze for:

1. **Bugs** — Logic errors, off-by-one, null/undefined access, race conditions
2. **Security** — Injection, XSS, CSRF, secrets exposure, insecure defaults
3. **Performance** — N+1 queries, unnecessary re-renders, memory leaks, large bundles
4. **Code Quality** — Dead code, unclear naming, missing error handling, DRY violations

Format each finding as:
- [SEVERITY: critical|high|medium|low] file:line — Description

Be specific. Reference exact lines. Skip obvious style issues.

--- DIFF START ---
{DIFF_CONTENT}
--- DIFF END ---
```
