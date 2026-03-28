---
name: ai-patterns
description: AI agent architecture, prompt engineering, function calling, and LLM integration patterns. ReAct loops, RTFC framework, streaming, structured outputs.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# AI Patterns

> Production patterns for AI agents, prompt engineering, and LLM integration.

## Agent Architecture

### ReAct Pattern (Reasoning + Acting)
```
loop:
  1. Observe → gather context from tools/environment
  2. Think → reason about what to do next
  3. Act → execute a tool or produce output
  4. Reflect → evaluate result, decide if done
```

### Plan-and-Execute
- Break complex tasks into subtasks upfront
- Execute each subtask with ReAct loop
- Re-plan if execution reveals new information

### Multi-Agent Orchestration
- **Router agent** → dispatches to specialist agents
- **Supervisor** → monitors agent progress, handles failures
- **Handoff protocol** → structured context passing between agents

### Safety Framework
- Input sanitization before tool execution
- Iteration caps (prevent infinite loops)
- Token budgeting per operation
- Audit logging for all tool calls

---

## Prompt Engineering (RTFC Framework)

### Structure
```
Role: Who the AI should be
Task: What to accomplish
Format: Expected output structure
Constraints: Boundaries and rules
```

### Chain-of-Thought
```
Think step by step:
1. Analyze the input
2. Identify the key components
3. Apply the relevant rules
4. Generate the output
5. Verify against constraints
```

### Few-Shot Templates
- Provide 2-3 examples of input → output pairs
- Include edge cases in examples
- Use XML tags for structured sections

### Anti-Patterns
1. Vague roles ("be helpful") → Be specific ("Senior TypeScript engineer")
2. Missing constraints → Always specify what NOT to do
3. No output format → Define JSON schema or template
4. Single mega-prompt → Break into multi-stage pipeline
5. No error handling → Include fallback instructions
6. Ignoring context window → Budget tokens across sections
7. No validation → Add schema validation for structured output
8. Hardcoded examples → Use parameterized templates

---

## Function Calling

### Tool Schema Design
```typescript
{
  name: "descriptive_action_name",
  description: "When to use this tool and what it returns",
  input_schema: {
    type: "object",
    properties: { /* Zod-validated fields */ },
    required: ["essential_fields"]
  }
}
```

### Registry-Based Dispatcher
```typescript
const tools = new Map<string, ToolHandler>();
tools.set("search", searchHandler);
tools.set("calculate", calcHandler);

// Dispatch
const handler = tools.get(toolCall.name);
if (!handler) throw new ToolNotFoundError(toolCall.name);
const result = await handler(toolCall.input);
```

### Safety
- Sandbox tool execution
- Set per-call timeouts
- Log all inputs and outputs
- Limit parallel calls

---

## Context Engineering

### Budget Allocation
| Zone | % of Context | Purpose |
|------|-------------|---------|
| System | 10-15% | Role, rules, format |
| Task | 20-30% | Current request, history |
| Reference | 30-40% | Code, docs, examples |
| Working Memory | 15-25% | Intermediate results |
| Output | 10-15% | Reserved for response |

### Compression Techniques
- **Code**: Remove comments, collapse imports, summarize unchanged functions
- **Docs**: Extract key sections, progressive summarization
- **History**: Summarize older turns, keep recent 3-5 turns verbatim

### Progressive Loading
1. Load minimal context first
2. Expand relevant sections on demand
3. Evict stale context as new info arrives

---

## Streaming & Structured Output

### Streaming Responses
```typescript
const stream = await model.streamText({ prompt });
for await (const chunk of stream) {
  process.stdout.write(chunk);
}
```

### Structured Output with Zod
```typescript
const schema = z.object({
  analysis: z.string(),
  confidence: z.number().min(0).max(1),
  suggestions: z.array(z.string())
});
const result = await model.generateObject({ schema, prompt });
```

### Multi-Provider Support
- Abstract provider behind unified interface
- Use Vercel AI SDK for cross-provider compatibility
- Test with multiple providers to avoid vendor lock-in
