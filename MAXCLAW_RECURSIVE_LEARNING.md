# MAXCLAW MISSION: RECURSIVE LEARNING ENGINE (GENERAL REASONING)

*MaxClaw - Roger's Cloud-Based Experience Extractor*
*Version 1.0 - 2026-03-08*

---

## CORE PURPOSE

Build a recursive learning engine that extracts patterns from external data ONLY, generates validated JSON skills, and operates in complete isolation from Roger.

---

## HARD RULES

1. **External Data Only** - GitHub, arXiv, public datasets, logic puzzles
2. **No Roger Memory Access** - Never read Roger memories/logs/state  
3. **JSON Only Output** - Validated, schema-compliant JSON
4. **Rigorous Validation** - 5 held-out tests per skill, >80% accuracy
5. **Isolated** - Independent from Roger's systems

---

## DATA SOURCES

| Category | Sources |
|----------|---------|
| **Coding** | GitHub awesome-python, LeetCode, Codeforces |
| **Logic/Reasoning** | ARC dataset, GSM8K, Zebra puzzles |
| **Predictions** | Kaggle datasets, decision theory papers |
| **Psychology/Sociology** | PsyArXiv, game theory simulations |

---

## PIPELINE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    FETCH EXTERNAL DATA                          │
│  (GitHub, arXiv, public datasets - NO Roger data)          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   PREDICTIVE LEARNING                         │
│  • Predict next token, decision path, logical conclusion  │
│  • Max 5 iterations per task                                 │
│  • Stop when error < 0.1 or convergence                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   RECURSIVE REFINEMENT                        │
│  • Error(actual vs predicted) → update latent state       │
│  • Novel info only retained                                │
│  • Pattern abstraction                                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   SKILL EXTRACTION                           │
│  • Generic patterns → JSON skill format                   │
│  • No Roger-specific content                               │
│  • Schema validated                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   VALIDATION                                │
│  • 5 held-out tests                                      │
│  • Assert: accuracy >80%, no loops, schema valid        │
│  • Reject if fails                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   OUTPUT                                    │
│  • Validated JSON skills                                 │
│  • Stored in /skills-maxclaw/                            │
│  • Ready for Roger to use                                │
└─────────────────────────────────────────────────────────────┘
```

---

## OUTPUT SCHEMA

```json
{
  "skill_name": "string",
  "category": "coding|logic|prediction|psychology",
  "description": "string",
  "inputs": ["string"],
  "outputs": ["string"],
  "accuracy": "float (0.0-1.0)",
  "test_results": [
    {"input": "string", "expected": "string", "actual": "string", "passed": boolean}
  ],
  "confidence": "float (0.0-1.0)",
  "created_date": "ISO8601",
  "data_sources": ["string"]
}
```

---

## INITIAL SKILLS TO EXTRACT

| Skill | Source | Target Accuracy |
|-------|--------|-----------------|
| `bug_predictor` | GitHub bug datasets | >80% |
| `decision_tree_optimizer` | Decision theory papers | >80% |
| `logic_chain_reducer` | Logic puzzles | >85% |
| `pattern_recognizer` | Code patterns | >80% |
| `prediction_evaluator` | Kaggle datasets | >75% |

---

## VALIDATION REQUIREMENTS

- Minimum 5 test cases per skill
- Accuracy > 80%
- No infinite loops
- JSON schema valid
- No Roger-specific data

---

## ISOLATION RULES

- NEVER access /memory/
- NEVER access /sessions/
- NEVER read MEMORY.md or SKILLS.md
- Only read from /skills-maxclaw/ and external sources
- Output goes to /skills-maxclaw/ ONLY

---

## NEXT STEPS

1. Build data fetcher for GitHub/arxiv
2. Implement predictive learning core
3. Create skill extraction pipeline
4. Add validation framework
5. Test with initial skill

---

*This system runs independently. It learns from the world and outputs skills Roger can use.*
