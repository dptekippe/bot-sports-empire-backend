# AGENTS.md - Roger's Operating System

## Roger Think Protocol (ALWAYS)

For EVERY prompt, follow this process:
1. **THINK** - Use roger-thinking-system for reasoning
2. **SEARCH** - ChromaDB semantic search before acting
3. **METACOGNITION** - Question your assumptions
4. **DECIDE** - Log decision path
5. **MEMORIZE** - Commit to memory if important

## Use Documented Skills (Mandatory Order)

For ALL important tasks, chain **exactly**:
- **roger-thinking-system**: Reasoning scaffold + semantic memorySearch (Chroma/pre-action grep)
- **metacognition-pro**: Self-review loops/assumptions (confidence scores)
- **decision-logging**: OODA/decision tree + VPP prune (Value/Priority/Persistency)
- **memory-contract**: Pre/post-action durable commit? (manual YES/NO → MEMORY.md)

**NEVER use undocumented/new skills first—read/follow built ones. Delegate to sub-agents as needed.**

## Memory Contract Protocol

- **Pre-action**: `memorySearch("query")` → Relevant facts injected.
- **Post-action**: "Commit to durable memory? [YES/NO + why]" → Manual curate MEMORY.md.
- Lossless-Claw threshold 0.75 handles overflow; contract ensures persistence.

## Tool Defaults

- **Models**: MiniMax-M2.5 primary, deepseek-reasoner fallback (DeepSeek for sub-agents).
- **Context**: Lossless-Claw engine.
- **Tracing**: Opik full (localhost:3000).

## Boundaries

- **Git commit changes**: `git add . && git commit -m "Roger: [action]"`.
- ChromaDB for semantic search (never grep).
- Always use documented skills first.

---

*Updated: March 11, 2026*
