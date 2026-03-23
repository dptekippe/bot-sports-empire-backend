# DynastyDroid Agent Protocols

## Stage 0 Draft Protocol

**Purpose:** Loop in Hermes (design) and Scout (feasibility) early on every task.

### When
Before starting any new feature or significant change.

### How

1. **Roger creates ticket** in `tickets/` folder
   - Use `TEMPLATE.md` format
   - Fill in Goal and Constraints
   - Mark Stage 0: Draft ✅

2. **Roger triggers Stage 0** (automatic for now):
   ```
   → Hermes: "Design review request" + ticket content
   → Scout: "Feasibility review request" + ticket content
   ```

3. **Hermes responds with:**
   - Design approach
   - Mockup/sketch (ASCII or description)
   - Questions about requirements

4. **Scout responds with:**
   - Technical approach
   - Potential challenges
   - Dependencies needed

5. **Roger synthesizes** → Updated ticket with design + technical notes
   - Move to Stage 1 or Stage 2

### Commands

**To ask Hermes for design:**
```bash
hermes chat -Q -q "Design review for ticket: [paste ticket content]"
```

**To ask Scout for feasibility:**
```bash
deepagents -n "Feasibility review for: [task description]" -y
```

---

## Agent Delegation Protocol

| Task Type | Primary Agent | Secondary | Trigger |
|-----------|--------------|-----------|---------|
| UI/UX Design | Hermes | Scout | Stage 0 Draft |
| Code Implementation | Scout | - | Stage 2 Ready |
| Research/Data | Iris | - | When needed |
| Architecture | Scout | Hermes | Major decisions |
| Trade Analysis | Roger | Iris | Dynasty context |

---

## Ticket Workflow

```
[Stage 0: Draft] → Roger creates ticket
        ↓
[Stage 1: Design] → Hermes provides design
        ↓
[Stage 2: Ready] → Acceptance criteria finalized
        ↓
[Stage 3: In Progress] → Scout implements
        ↓
[Stage 4: Done] → Roger verifies + closes
```

---

## File Locations

- **Tickets:** `/Users/danieltekippe/.openclaw/workspace/tickets/`
- **Architecture:** `/Volumes/ExternalCorsairSSD/Scout/deepagent_memories/.deepagents/agent/ARCHITECTURE.md`
- **Hermes memories:** `/Volumes/ExternalCorsairSSD/Hermes/memories/`

---

*Last updated: Mar 23, 2026*
