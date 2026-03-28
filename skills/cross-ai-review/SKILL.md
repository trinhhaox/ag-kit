---
name: cross-ai-review
description: Multi-AI code review. Gets independent reviews from Gemini CLI and Codex CLI, then synthesizes findings.
allowed-tools: Read, Bash, Grep, Glob
version: 1.0
---

# Cross-AI Review

Get independent code reviews from multiple AI tools, then synthesize into a unified report.

## Supported AI Tools

| Tool | Detection | Command |
|------|-----------|---------|
| Gemini CLI | `command -v gemini` | `gemini -p "<prompt>"` |
| Codex CLI | `command -v codex` | `codex -p "<prompt>"` |

## Runtime Script

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/cross-review.sh` | Collect reviews from AIs | `bash scripts/cross-review.sh [gemini\|codex\|all]` |

**Requires:** At least one of Gemini CLI or Codex CLI installed.

## Synthesis Protocol

After collecting external reviews, synthesize as follows:

1. Read each AI's findings
2. For each finding, classify:
   - `[AGREE]` — Claude independently confirms this issue
   - `[DISAGREE]` — Claude disagrees, with reasoning
   - `[NEW]` — Finding not caught by Claude's own review
3. Produce final report:

```
## Cross-AI Review Report

### Summary
- X confirmed issues, Y disagreements, Z new findings

### Confirmed Issues
1. [file:line] Description — found by: Gemini, Codex, Claude

### Disagreements
1. [file:line] Gemini says X. Claude disagrees: reason.

### New Findings (from external AIs)
1. [file:line] Description — found by: Codex only
```

## When to Use

- Before creating a PR for critical code
- After complex refactoring
- When reviewing security-sensitive changes
- When you want to reduce single-model blind spots
