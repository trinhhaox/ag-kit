---
name: context-engineering
description: LLM context window optimization - budget allocation, compression, progressive loading, RAG retrieval patterns for efficient AI interactions.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Context Engineering

> Optimize how information is fed to LLMs for maximum output quality.

## Context Budget Model

### 5-Zone Allocation
```
┌─────────────────────────────┐
│ System Instructions  10-15% │ Role, rules, output format
├─────────────────────────────┤
│ Task Context         20-30% │ Current request, conversation history
├─────────────────────────────┤
│ Reference Material   30-40% │ Code, docs, examples, search results
├─────────────────────────────┤
│ Working Memory       15-25% │ Intermediate reasoning, tool results
├─────────────────────────────┤
│ Output Reserve       10-15% │ Space for the response
└─────────────────────────────┘
```

### Token Budgeting
```typescript
const CONTEXT_LIMIT = 200000; // Claude's context window
const budget = {
  system: Math.floor(CONTEXT_LIMIT * 0.12),
  task: Math.floor(CONTEXT_LIMIT * 0.25),
  reference: Math.floor(CONTEXT_LIMIT * 0.35),
  working: Math.floor(CONTEXT_LIMIT * 0.18),
  output: Math.floor(CONTEXT_LIMIT * 0.10),
};
```

---

## Compression Techniques

### Code Compression
```
Full file (expensive):
  → Remove comments and blank lines
  → Collapse import blocks to summary
  → Show only changed functions in full
  → Summarize unchanged functions as signatures only
```

### Document Compression
```
Full document:
  → Extract headings + first sentence per section
  → Keep code examples, remove prose
  → Progressive: summary → relevant sections → full text
```

### Conversation Compression
```
Turn 1-5 (old): Summarize to 2-3 sentences
Turn 6-8 (recent): Keep key decisions and outcomes
Turn 9-10 (current): Keep verbatim
```

---

## Progressive Loading Strategy

### Level 1: Structural Overview
```
Read file tree → understand project layout
Read function signatures → understand API surface
Read type definitions → understand data model
```

### Level 2: Targeted Detail
```
Read specific function bodies relevant to task
Read test files for the module being modified
Read config files affecting behavior
```

### Level 3: Deep Context
```
Read related modules for side effects
Read git history for recent changes
Read documentation for design decisions
```

### Decision Rule
> Load the minimum context needed to make a correct decision.
> If uncertain, load one more level, not everything.

---

## RAG (Retrieval-Augmented Generation)

### Retrieval Strategy (Priority Order)
1. **Exact match** — function name, error message, file path
2. **Semantic search** — vector embedding similarity
3. **Keyword search** — BM25 / full-text search
4. **Structural search** — AST-based code search

### Document Ranking
```typescript
type SearchResult = {
  content: string;
  score: number;       // Relevance score
  source: string;      // File path or URL
  freshness: number;   // How recent (0-1)
  authority: number;   // Source trustworthiness (0-1)
};

// Composite ranking
const finalScore = (r: SearchResult) =>
  r.score * 0.5 + r.freshness * 0.3 + r.authority * 0.2;
```

### Chunking Strategies
| Strategy | Chunk Size | Overlap | Use When |
|----------|-----------|---------|----------|
| Fixed-size | 500-1000 tokens | 100 tokens | General text |
| Semantic | By paragraph/section | None | Structured docs |
| Code-aware | By function/class | Include imports | Source code |
| Recursive | Split by headers, then paragraphs | Minimal | Long documents |

---

## Context Quality Signals

### Include (High Value)
- Type definitions and interfaces
- Function signatures with JSDoc
- Error messages and stack traces
- Test cases (show expected behavior)
- Recent git diff (shows intent)

### Exclude (Low Value)
- Lock files (package-lock.json)
- Generated code (dist/, .next/)
- Binary files
- Redundant imports across files
- Unchanged boilerplate

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Dump entire file | Wastes context, dilutes signal | Extract relevant functions only |
| No context | Hallucination, incorrect assumptions | Provide minimum viable context |
| Stale context | Outdated info causes wrong decisions | Refresh before each major step |
| Repeated context | Same info in system + task + reference | Deduplicate across zones |
| Over-retrieval | Too many RAG results overwhelm | Top-k=5, re-rank, filter by score threshold |
