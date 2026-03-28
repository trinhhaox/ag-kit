---
description: Cross-AI code review. Collects reviews from Gemini and Codex CLIs, then synthesizes findings.
---

# /review-cross - Cross-AI Code Review

$ARGUMENTS

---

## Task

Get independent code reviews from multiple AI tools and synthesize findings.

### Usage

```
/review-cross              # Review with all available AIs
/review-cross --ai gemini  # Gemini only
/review-cross --ai codex   # Codex only
/review-cross --ai all     # Explicitly all
```

### Steps

1. **Collect external reviews**
   - Run: `bash .agent/skills/cross-ai-review/scripts/cross-review.sh {ai_target}`
   - Wait for all AI tools to respond (timeout: 2 min each)

2. **Read Claude's own review**
   - Review the same diff independently before reading external findings
   - Note your own findings first

3. **Synthesize**
   - Read the cross-ai-review skill's synthesis protocol
   - For each external finding: classify as AGREE / DISAGREE / NEW
   - Produce the unified report format from the skill

4. **Present to user**
   - Show the Cross-AI Review Report
   - Highlight critical/high severity items
   - Flag disagreements for human decision
