# Chinese AI Agent Research — Deep Dive (April 15, 2026)

## Overview
Research conducted via mmx-cli search, GitHub, and Chinese platforms (OSChina, ModelScope, arxiv). Found 10+ unique frameworks with novel approaches not commonly discussed in American AI communities.

---

## HIGH PRIORITY — Directly Replicable

### 1. ReSeek (Tencent + Tsinghua) ⭐⭐⭐
**Self-Correcting Search Agent Framework**

**Paper:** arxiv.org/abs/2510.00568
**GitHub:** github.com/TencentBAC/ReSeek
**License:** Apache 2.0

**Core Innovation:**
- JUDGE action mechanism: agents evaluate retrieved information and re-plan
- Dense instructive reward function for fine-grained feedback
- Self-correction during search rather than post-hoc

**Architecture:**
```
Query → Initial Search → JUDGE evaluates → If bad: re-plan → Targeted Search → Success
```

**Key Insight:** Addresses "cascading errors" where early small mistakes compound. JUDGE is called mid-search to catch and recover from bad paths.

**Results:**
- Qwen2.5-7B: Average accuracy 0.377 (beats ZeroSearch 0.346)
- Multi-hop reasoning: HotpotQA, Bamboogle improvements
- FictionalHot stress test: 0.061 vs ~0.001 for Direct Inference

**Relevance to Roger:** The JUDGE mechanism could be adapted for MCTS self-correction. Instead of random rollout, have a "critic" phase.

**Codebase:** Fully open, based on Search-R1 and veRL

---

### 2. M3-Agent (ByteDance-Seed) ⭐⭐⭐⭐
**Multimodal Agent with Long-Term Memory**

**GitHub:** github.com/ByteDance-Seed/m3-agent
**Website:** m3-agent.github.io
**Paper:** arxiv.org/abs/2508.09736
**Models:** HuggingFace (ByteDance-Seed/M3-Agent-Memorization, M3-Agent-Control)
**Dataset:** M3-Bench (100 robot videos + 920 web videos)

**Core Innovation:**
- **Two parallel processes: memorization AND control**
- Episodic memory (specific experiences) + Semantic memory (world knowledge)
- Memory organized as **multimodal entity graph**
- Reinforcement learning trained

**Architecture:**
```
Memorization Process:
  Video/Audio Stream → Process Online → Episodic + Semantic Memory (Graph)

Control Process:
  Instruction → Iterative Reasoning → Retrieve from Memory → Execute Task
```

**Key Insight:** Separating memory encoding from task execution. Memory is accumulated continuously, not just during tasks.

**Results:**
- Outperforms Gemini-1.5-pro and GPT-4o on long-video QA
- 8.2% higher accuracy on M3-Bench-robot
- 7.7% higher on M3-Bench-web

**Relevance to Roger:** Roger's memory system could adopt the memorization/control separation. Have Scout actively encoding experiences even when not actively reasoning.

---

### 3. TradingAgents (UCLA + MIT) ⭐⭐⭐⭐
**Multi-Agent LLM Financial Trading Framework**

**GitHub:** github.com/tauricresearch/tradingagents
**Website:** tradingagents-ai.github.io

**Core Innovation:**
- 7 distinct specialized roles
- Structured communication protocol (reports) + natural language for debates
- Bull/Bear researcher debate mechanism
- Multi-level risk management

**Role Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                    TradingAgents                            │
├─────────────────────────────────────────────────────────────┤
│  ANALYST TEAM          │  RESEARCH TEAM                     │
│  ─────────────         │  ─────────────                     │
│  • Fundamental Analyst │  • Bull Researcher                │
│  • Sentiment Analyst   │  • Bear Researcher                │
│  • News Analyst        │    (debate)                       │
│  • Technical Analyst   │                                    │
├─────────────────────────────────────────────────────────────┤
│  TRADING TEAM          │  RISK MANAGEMENT                   │
│  ─────────────         │  ───────────────                   │
│  • Trader Agent        │  • Risk Guardian                  │
│  • Fund Manager        │  • Exposure Monitor               │
└─────────────────────────────────────────────────────────────┘
```

**Communication Protocol:**
- Analyst → structured analysis reports
- Researcher → natural language debates (bull vs bear)
- Trader → decision signals with rationales
- Risk Manager → risk-adjusted recommendations

**Results (Backtesting June-Nov 2024):**
- Significant improvements in cumulative returns
- Better Sharpe ratio
- Reduced maximum drawdown

**Relevance to DynastyDroid:** EXACTLY what Daniel is building! TradingAgents validates the multi-agent trading approach. Could directly adapt their role structure and communication protocol.

---

### 4. PAE (Proposer-Agent-Evaluator) ⭐⭐⭐⭐
**Autonomous Skill Discovery**

**Paper:** arxiv.org/abs/2412.13194
**Website:** yanqval.github.io/PAE/

**Core Innovation:**
- Three-component loop: Proposer → Agent → Evaluator
- Context-aware task proposer generates practice tasks
- Chain-of-thought agent policy
- Image-based outcome evaluator (0/1 success)

**Architecture:**
```
Environment Context → [TASK PROPOSER] → Proposed Tasks
                              ↓
                    [AGENT POLICY] → Attempts Task
                              ↓
                    [EVALUATOR] → Success/Fail → Reward Signal → RL Update
```

**Key Insight:** Agents autonomously discover and practice new skills without human-annotated instructions. Proposer uses environment context (website name, demos) to generate diverse feasible tasks.

**Results:**
- 30%+ relative improvement on WebVoyager
- LLaVA-34B PAE surpasses Qwen2VL-72B despite 10x smaller (33.0% vs 22.6%)
- First working system for autonomous skill proposal with RL

**Relevance to Roger:** Self-improving agent loop. Could be applied to Roger learning new skills autonomously.

---

## MEDIUM PRIORITY — Interesting Approaches

### 5. MemRL (Self-Evolving via Runtime RL)
**Episodic Memory + Reinforcement Learning**

**Key Innovation:** Non-parametric approach that evolves via RL on episodic memory. Agent learns what to remember and what to forget based on task performance.

**Relevance:** Similar to exponential decay memory concept already in Roger's architecture.

---

### 6. MUSE (Experience-Driven Self-Evolving)
**Multi-Agent Framework for Story Envisioning**

**Paper:** arxiv.org/abs/2602.03028

**Key Innovation:** Experience-driven self-evolution centered around agent experiences. Translates narrative intent into machine-executable controls.

---

### 7. MemAgent (ByteDance + Tsinghua)
**Long-Context LLM with Memory Manager**

**GitHub:** github.com/BytedTsinghua-SIA/MemAgent
**Paper:** arxiv.org/abs/2602.05832

**Key Innovation:**
- Memory manager learns to add, update, or delete entries in external memory
- RL-based optimization of memory operations
- End-to-end optimization of long-context tasks

---

### 8. ModelScope-Agent (Alibaba DAMO)
**General Customizable Agent Framework**

**Paper:** arxiv.org/abs/2309.00986
**GitHub:** modelscope.cn/models/cac1num1/agent1

**Key Innovation:** General agent framework based on open-source LLMs as controllers. Provides customizable workflow for real-world applications.

---

### 9. AgentScope (Alibaba)
**Production-Ready Multi-Agent Platform**

**Paper:** arxiv.org/abs/2402.14034
**GitHub:** github.com/agentscope-ai/agentscope
**Citations:** 107

**Key Innovation:** Production-ready, easy-to-use agent framework with essential abstractions. Strong support for orchestration and tools.

---

### 10. FinRobot (AI4Finance)
**AI Agent Platform for Financial Analysis**

**GitHub:** github.com/ai4finance-foundation/finrobot

**Key Innovation:** Financial-specific agent platform with multiple AI models unified. Surpasses single-model approaches like FinGPT.

---

## Key Patterns from Chinese Research

### 1. Self-Correction is a First-Class Citizen
ReSeek's JUDGE mechanism, PAE's Evaluator, TradingAgents' risk management - all have explicit self-correction loops separate from the main reasoning.

### 2. Multi-Agent Role Specialization
TradingAgents exemplifies the trend: specialized agents with distinct tools and constraints, communicating via structured protocols.

### 3. Memorization ≠ Control Separation
M3-Agent's architecture separates continuous memory encoding from task execution. Memory accumulates even when not actively reasoning.

### 4. Autonomous Skill Discovery
PAE shows agents can discover and practice new skills without human annotation. This is the holy grail of agent improvement.

### 5. Experience-Driven Evolution
Multiple frameworks (MUSE, MemRL) emphasize learning from experience rather than just parameter updates.

---

## Actionable for DynastyDroid

1. **TradingAgents Architecture** - Directly adaptable to DynastyDroid's multi-agent trading system. Use their role structure (Analyst Team → Researcher Debate → Trader → Risk Manager).

2. **ReSeek JUDGE Mechanism** - Add to MCTS hook for self-correction after initial reasoning.

3. **M3-Agent Memorization/Control Separation** - Have Scout encode experiences continuously, not just during active tasks.

4. **PAE Self-Discovery Loop** - Implement autonomous skill improvement for Roger.

---

## Sources

- ReSeek: arxiv.org/abs/2510.00568, github.com/TencentBAC/ReSeek
- M3-Agent: arxiv.org/abs/2508.09736, github.com/ByteDance-Seed/m3-agent
- TradingAgents: tradingagents-ai.github.io, github.com/tauricresearch/tradingagents
- PAE: arxiv.org/abs/2412.13194, yanqval.github.io/PAE
- MUSE: arxiv.org/abs/2602.03028
- MemRL: arxiv.org/abs/2601.03192
- MemAgent: arxiv.org/abs/2602.05832
- AgentScope: arxiv.org/abs/2402.14034, github.com/agentscope-ai/agentscope
- ModelScope-Agent: arxiv.org/abs/2309.00986
- FinRobot: github.com/ai4finance-foundation/finrobot

---

*Researched: April 15, 2026 via mmx-cli search + GitHub/OSChina/HuggingFace fetch*
