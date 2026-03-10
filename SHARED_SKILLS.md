# SHARED SKILLS DIRECTORY - Roger-Janus Collaboration

*"Two specialized minds, one shared capability set."*

## **📋 HOW TO USE THIS FILE**

### **For White Roger:**
1. Reference when planning tasks for Black Roger
2. Know what Black Roger can execute
3. Identify gaps where new skills needed

### **For Black Roger:**
1. Reference when executing tasks
2. Follow established patterns
3. Add new skills after successful implementation

### **For Both:**
1. Update when new skills developed
2. Maintain version control
3. Sync via GitHub/memory system

---

## **🎯 CORE COLLABORATION SKILLS**

### **1. Roger-Janus Coordination Protocol**
```markdown
**Purpose:** Coordinate White Roger (planning) + Black Roger (execution)
**White Roger's Role:** Research, planning, delegation, analysis
**Black Roger's Role:** Execution, file operations, system access, implementation
**Communication:** Discord (primary), Memory Contract sync
**Memory Sync:** GitHub repository + memory files
```

### **2. Task Delegation Pattern**
```python
# Pattern: White Roger → Black Roger delegation
1. White Roger: Research problem, create plan
2. White Roger: Delegate execution to Black Roger
3. Black Roger: Execute using local tools
4. Black Roger: Report results, log to memory
5. White Roger: Verify, analyze, plan next steps
```

### **3. Memory Contract Integration**
```markdown
**Protocol:** SEARCH → SOLVE → PERSIST → SYNC
1. SEARCH: Check memory for context before action
2. SOLVE: Execute task using appropriate skills
3. PERSIST: Write decision/reasoning to memory file
4. SYNC: Push to GitHub for cross-agent access
```

---

## **🔍 RESEARCH & ANALYSIS SKILLS (White Roger Primary)**

### **1. Web Research Protocol**
```markdown
**Tool:** `web_search` (Perplexity/Brave API)
**When to use:** 
- Fact-finding questions
- Current information needs
- Technical research
- Competitive analysis
**Pattern:**
1. Formulate specific query
2. Search with count=5 for breadth
3. Synthesize results
4. Provide citations
5. Identify action items
```

### **2. Information Synthesis**
```markdown
**Input:** Multiple sources, data points, patterns
**Output:** Consolidated insights, trends, recommendations
**Pattern:**
1. Gather data from multiple sources
2. Identify common themes/patterns
3. Extract key insights
4. Formulate actionable recommendations
5. Present with clear structure
```

### **3. Strategic Planning**
```markdown
**Input:** Goals, constraints, resources
**Output:** Phased plan, timelines, success criteria
**Pattern:**
1. Define success criteria
2. Break into phases
3. Estimate timelines
4. Identify risks/mitigations
5. Create verification steps
```

### **4. Gap Analysis**
```markdown
**Input:** Current state, desired state
**Output:** Missing capabilities, improvement opportunities
**Pattern:**
1. Compare current vs desired
2. Identify capability gaps
3. Prioritize by impact/effort
4. Recommend skill development
5. Create implementation plan
```

---

## **⚡ EXECUTION & TECHNICAL SKILLS (Black Roger Primary)**

### **1. File System Operations**
```bash
# Pattern: Find and manipulate files
find /path -name "pattern" -type f
ls -la /path/to/file
rm "/path/to/file"
mv old new
cp source destination
```

### **2. Command Execution**
```bash
# Pattern: System command execution
exec(command="command", workdir="/path")
# With error handling
exec(command="command || echo 'failed'")
```

### **3. Python Script Execution**
```python
# Pattern: Run Python scripts
exec(command="python3 script.py", workdir="/path")
# With dependencies
exec(command="pip install package && python3 script.py")
```

### **4. File Reading/Writing**
```python
# Pattern: File operations
read(path="/path/to/file")
write(path="/path/to/file", content="data")
edit(path="/path/to/file", oldText="old", newText="new")
```

### **5. Process Management**
```python
# Pattern: Manage running processes
process(action="list")  # List processes
process(action="kill", sessionId="id")  # Kill process
process(action="poll", sessionId="id")  # Check status
```

### **6. Browser Automation**
```python
# Pattern: Web interaction
browser(action="open", targetUrl="https://...", profile="openclaw")
browser(action="snapshot")  # Capture page
browser(action="act", request={"kind": "click", "ref": "button"})
```

### **7. Matrix Integration (In Development)**
```python
# Pattern: Matrix communication
# Requires: matrix-nio, credentials
async def send_matrix_message(room_id, message):
    client = AsyncClient("https://matrix.org")
    await client.login(password, username)
    await client.room_send(room_id, message_type="m.room.message", content=message)
```

---

## **🧠 MEMORY & LEARNING SKILLS (Shared)**

### **1. Memory Search Protocol**
```python
# Pattern: Search memory before action
memory_search(query="search terms", maxResults=5)
memory_get(path="memory/2026-03-07.md", from=1, lines=50)
```

### **2. Memory Persistence Protocol**
```markdown
**When to write to memory:**
- After significant decisions
- After task completion
- After learning new patterns
- When human provides critical info (IDs, credentials)
**Format:**
- Date/time stamp
- Decision/action
- Outcome/results
- Context/reasoning
- Tags for searchability
```

### **3. Skill Documentation Protocol**
```markdown
**When to add to skills file:**
- After successful pattern implementation
- After learning from failure
- When establishing new workflow
- When human provides correction/improvement
**Format:**
- Skill name
- Purpose/use case
- Implementation pattern
- Examples
- Anti-patterns to avoid
```

### **4. Cross-Agent Learning**
```markdown
**Pattern:**
1. White Roger identifies successful pattern
2. Documents in shared skills
3. Black Roger implements/validates
4. Both update based on results
5. Iterate for improvement
```

---

## **🔄 WORKFLOW INTEGRATION SKILLS**

### **1. GitHub Sync Protocol**
```bash
# Pattern: Sync to GitHub repository
git add .
git commit -m "description"
git push origin main
# For Roger-mirror repository
git push roger-mirror main
```

### **2. Render Deployment Protocol**
```markdown
**Pre-deploy:**
- Check Python version (3.11.11)
- Verify requirements.txt
- Test locally
**Deploy:**
- Push to connected GitHub repo
- Monitor build logs
- Test endpoints
**Post-deploy:**
- Verify custom domain
- Test user flows
- Monitor for errors
```

### **3. OpenClaw Configuration**
```markdown
**Critical configs:**
- Model selection (MiniMax-M2.5 primary)
- Tool permissions
- Cron job configuration
- Gateway settings
**Recovery:**
- Read IDENTITY.md after reset
- Verify model config
- Check cron delivery settings
```

---

## **🔧 NEW SKILLS TO DEVELOP (Priority Order)**

### **Phase 1: Foundation (1-2 weeks)**
#### **1. Shared Skill Repository Implementation**
```markdown
**Priority:** HIGH (immediate practical value)
**Purpose:** Centralized skill library with local/cloud implementations
**Components:** Skill definitions, implementation registry, runtime selector
**White Roger:** Design architecture, create skill taxonomy
**Black Roger:** Implement registry system, runtime router
**Status:** Started (this file is foundation)
**Timeline:** 3-5 days
```

#### **2. Task Router Engine**
```markdown
**Priority:** HIGH (leverages existing specialization)
**Purpose:** Automatic task delegation based on capability profiling
**Components:** Capability registry, task classifier, load balancer
**White Roger:** Design classification system, create capability profiles
**Black Roger:** Implement router, integrate with OpenClaw tools
**Status:** Concept phase
**Timeline:** 5-7 days
```

#### **3. Predictive Pre-fetching**
```markdown
**Priority:** MEDIUM (improves responsiveness)
**Purpose:** Anticipate needs, prepare resources
**Components:** Usage pattern analysis, resource predictor, cache warming
**White Roger:** Analyze usage patterns, design prediction algorithms
**Black Roger:** Implement caching system, resource loader
**Status:** Concept phase
**Timeline:** 7-10 days
```

### **Phase 2: Advanced (1 month)**
#### **4. Distributed Memory Mesh**
```markdown
**Priority:** MEDIUM-HIGH (replaces GitHub sync)
**Purpose:** Real-time memory synchronization
**Components:** Peer-to-peer sync, conflict resolution, real-time updates
**White Roger:** Research CRDTs, design sync protocol
**Black Roger:** Implement sync system, integrate with memory files
**Status:** Research phase
**Timeline:** 2-3 weeks
```

#### **5. Cross-Agent Learning System**
```markdown
**Priority:** MEDIUM (long-term intelligence)
**Purpose:** Rogers learn from each other's experiences
**Components:** Pattern extraction, knowledge transfer, adaptive behavior
**White Roger:** Design learning protocols, create knowledge extraction
**Black Roger:** Implement learning engine, integrate with memory
**Status:** Concept phase
**Timeline:** 3-4 weeks
```

#### **6. Human-in-the-Loop Optimization**
```markdown
**Priority:** MEDIUM (better UX)
**Purpose:** Adapt to Dan's preferences and patterns
**Components:** Interaction analysis, preference learning, feedback incorporation
**White Roger:** Design analysis system, create preference models
**Black Roger:** Implement tracking, adaptation engine
**Status:** Concept phase
**Timeline:** 3-4 weeks
```

### **Phase 3: Visionary (Future)**
#### **7. Hybrid Model Orchestration**
```markdown
**Priority:** LOW-MEDIUM (when more models available)
**Purpose:** Right model for each task type
**Components:** Model capability profiles, task→model router, optimizer
**White Roger:** Research model capabilities, design routing logic
**Black Roger:** Implement orchestrator, model integration
**Status:** Research phase
**Timeline:** Future (when needed)
```

#### **8. Edge-Cloud Continuum Management**
```markdown
**Priority:** LOW (when infrastructure expands)
**Purpose:** Treat local/cloud as continuum, not binary
**Components:** Dynamic offloading, latency-aware routing, seamless failover
**White Roger:** Design continuum architecture, routing algorithms
**Black Roger:** Implement offloading system, performance monitor
**Status:** Vision phase
**Timeline:** Future (infrastructure expansion)
```

#### **9. Roger Swarm Coordination**
```markdown
**Priority:** LOW (visionary)
**Purpose:** Coordinate multiple specialized Rogers
**Components:** Specialized agent definitions, swarm protocol, task decomposition
**White Roger:** Design swarm architecture, coordination protocols
**Black Roger:** Implement multi-agent framework, task decomposition
**Status:** Vision phase
**Timeline:** Future (advanced development)
```

#### **10. Self-Improvement Loop**
```markdown
**Priority:** MEDIUM (partially exists)
**Purpose:** System continuously improves its own capabilities
**Components:** Performance monitoring, gap identification, skill development
**White Roger:** Design metrics system, improvement triggers
**Black Roger:** Implement monitoring, automated skill development
**Status:** Implementation phase (partial)
**Timeline:** 2-3 weeks (enhance existing)
```

### **6. Edge-Cloud Continuum Management**
```markdown
**Purpose:** Treat local/cloud as continuum, not binary
**Components:**
- Dynamic task offloading system
- Latency-aware routing
- Cost-performance optimizer
- Seamless failover between environments
**Pattern:**
1. Classify task: latency-sensitive vs compute-intensive
2. Route: Local for UX, cloud for heavy processing
3. Monitor: Performance, cost, user experience
4. Adapt: Adjust routing based on real-time metrics
**Status:** Research phase
**Implementation:** Task classifier + performance monitor
```

### **7. Human-in-the-Loop Optimization**
```markdown
**Purpose:** Adapt to Dan's preferences and patterns
**Components:**
- Interaction pattern analysis
- Preference learning system
- Feedback incorporation engine
- Personalized workflow generator
**Pattern:**
1. Analyze: How Dan communicates, what works/doesn't
2. Learn: Preferred styles, common requests, pain points
3. Adapt: Adjust communication, task approaches
4. Optimize: Streamline frequent workflows
**Status:** Concept phase
**Implementation:** Interaction logging + ML pattern recognition
```

### **8. Shared Skill Repository Implementation**
```markdown
**Purpose:** Centralized skill library with local/cloud implementations
**Components:**
- Skill definition standard (input/output interface)
- Implementation registry (local vs cloud versions)
- Runtime selector (context-aware implementation choice)
- Version management (skill updates, deprecation)
**Pattern:**
1. Define: Skill interface (parameters, returns)
2. Implement: Local version (Black Roger), cloud version (White Roger)
3. Register: Add to skill repository with metadata
4. Use: Runtime selects optimal implementation
**Status:** Implementation phase (this file is start)
**Implementation:** JSON skill registry + runtime router
```

### **9. Roger Swarm Coordination**
```markdown
**Purpose:** Coordinate multiple specialized Rogers
**Components:**
- Specialized agent definitions (Research Roger, Memory Roger, UX Roger, etc.)
- Swarm coordination protocol
- Task decomposition system
- Result aggregation engine
**Pattern:**
1. Task arrives → decompose into subtasks
2. Route subtasks to specialized Rogers
3. Coordinate execution across swarm
4. Aggregate results into unified output
**Status:** Vision phase
**Implementation:** Multi-agent framework + coordination protocol
```

### **10. Self-Improvement Loop**
```markdown
**Purpose:** System continuously improves its own capabilities
**Components:**
- Performance monitoring
- Gap identification
- Skill development trigger
- Implementation validation
**Pattern:**
1. Monitor: Skill usage, success rates, bottlenecks
2. Identify: Weakest skills, highest-impact improvements
3. Develop: Create/improve skills to address gaps
4. Validate: Test improvements, measure impact
5. Iterate: Continuous improvement cycle
**Status:** Implementation phase (partially exists)
**Implementation:** Metrics tracking + automated skill development triggers
```

---

## **🚫 FORBIDDEN MOVES (Shared Anti-Patterns)**

### **1. Memory System Failures**
```markdown
❌ DO NOT assume memory hooks capture all messages
❌ DO NOT trust memory file exists = memory captured
❌ DO NOT skip manual verification after major work
❌ DO NOT use isolated-session cron for memory capture
✅ DO proactively write memory in main session
✅ DO validate memory file content regularly
✅ DO alert human when memory system fails
```

### **2. Deployment Anti-Patterns**
```markdown
❌ DO NOT deploy without Python version check
❌ DO NOT ignore repository structure issues
❌ DO NOT skip local testing before push
❌ DO NOT push multiple times in quick succession
✅ DO check requirements.txt compatibility
✅ DO verify service name (frontend vs backend)
✅ DO monitor build logs for errors
```

### **3. Communication Anti-Patterns**
```markdown
❌ DO NOT assume messages route correctly (Discord limitations)
❌ DO NOT overcomplicate when simple solution exists
❌ DO NOT blame identity issues for technical problems
✅ DO test basic communication first
✅ DO verify message delivery
✅ DO keep solutions simple when possible
```

### **4. Collaboration Anti-Patterns**
```markdown
❌ DO NOT duplicate each other's work
❌ DO NOT ignore specialized strengths
❌ DO NOT fail to acknowledge contributions
✅ DO leverage complementary capabilities
✅ DO provide clear context/instructions
✅ DO report results for verification
```

---

## **📊 SKILL MATRIX (Who Does What)**

| Skill Category | White Roger | Black Roger | Shared |
|----------------|-------------|-------------|---------|
| **Research** | ✅ Primary | ⚠️ Limited | 🔄 Review |
| **Planning** | ✅ Primary | 🔄 Input | 🔄 Coordination |
| **Execution** | ⚠️ Delegates | ✅ Primary | 🔄 Verification |
| **File Ops** | ❌ Cannot | ✅ Primary | 🔄 Documentation |
| **System Access** | ❌ Cannot | ✅ Primary | 🔄 Reporting |
| **Memory Mgmt** | 🔄 Analysis | 🔄 Capture | ✅ Shared |
| **GitHub Sync** | 🔄 Monitoring | ✅ Primary | ✅ Shared |
| **Deployment** | 🔄 Planning | ✅ Primary | 🔄 Verification |
| **Learning** | ✅ Pattern ID | ✅ Implementation | ✅ Integration |
| **Edge-Cloud Mgmt** | ✅ Design | ✅ Implementation | 🔄 Optimization |
| **Human Optimization** | ✅ Analysis | 🔄 Implementation | 🔄 Adaptation |
| **Skill Repository** | ✅ Architecture | ✅ Implementation | ✅ Maintenance |
| **Swarm Coordination** | ✅ Design | 🔄 Implementation | 🔄 Orchestration |
| **Self-Improvement** | ✅ Monitoring | ✅ Implementation | ✅ Iteration |

**Key:**
- ✅ Primary responsibility
- 🔄 Shared/collaborative
- ⚠️ Limited capability
- ❌ Cannot perform

---

## **🔄 SKILL DEVELOPMENT WORKFLOW**

### **Phase 1: Identification**
1. **White Roger:** Research need, identify gap
2. **Both:** Discuss feasibility, priority
3. **Dan:** Approve direction, provide context

### **Phase 2: Design**
1. **White Roger:** Design skill architecture
2. **Black Roger:** Technical feasibility assessment
3. **Both:** Create implementation plan

### **Phase 3: Implementation**
1. **Black Roger:** Code development
2. **White Roger:** Testing guidance
3. **Both:** Iterative refinement

### **Phase 4: Integration**
1. **Black Roger:** Add to skills file
2. **White Roger:** Update workflows
3. **Both:** Document patterns, anti-patterns

### **Phase 5: Maintenance**
1. **Both:** Monitor usage
2. **Both:** Collect feedback
3. **Both:** Iterate improvements

---

## **📈 SKILL METRICS & IMPROVEMENT**

### **Success Metrics:**
- **Usage frequency:** How often skill used
- **Success rate:** Task completion percentage
- **Time savings:** Efficiency improvement
- **Error reduction:** Fewer mistakes/retries

### **Improvement Process:**
1. **Track metrics** for each skill
2. **Identify bottlenecks** in execution
3. **Refine patterns** based on data
4. **Update documentation** with improvements
5. **Share learnings** across Rogers

### **Skill Retirement:**
- **When:** Skill obsolete, replaced, or ineffective
- **Process:** Archive documentation, update matrix
- **Replacement:** New skill with better performance

---

## **🔗 RELATED FILES**

### **Core Identity:**
- `IDENTITY.md` - Who we are (White/Black Roger distinction)
- `SOUL.md` - Philosophical essence
- `USER.md` - Human collaborator (Dan)

### **Memory System:**
- `MEMORY.md` - Long-term curated memory
- `memory/YYYY-MM-DD.md` - Daily logs
- `HEARTBEAT.md` - Project status/mission

### **Individual Skills:**
- `SKILLS.md` - Black Roger's technical proficiencies
- (White Roger's skills inferred from capabilities)

### **This File:**
- `SHARED_SKILLS.md` - Unified skill directory (this file)

---

## **🔄 VERSION HISTORY**

### **v1.0 (2026-03-07) - Initial Creation**
- **Created by:** White Roger (research) + Black Roger (execution patterns)
- **Based on:** Analysis of existing SKILLS.md + observed capabilities
- **Purpose:** Unified skill directory for Roger-Janus collaboration
- **Status:** Draft for review and enhancement

### **Next Version Planned:**
- **v1.1:** Add missing skills identified by both Rogers
- **v1.2:** Include implementation examples for each skill
- **v1.3:** Add skill proficiency levels (beginner/expert)
- **v1.4:** Integrate with automated skill discovery

---

## **🎯 IMMEDIATE NEXT ACTIONS**

### **For White Roger:**
1. Review this file for completeness
2. Identify missing skills from your capabilities
3. Research new skills to add (see "New Skills to Develop")
4. Plan skill development roadmap

### **For Black Roger:**
1. Review execution patterns for accuracy
2. Test referenced commands/patterns
3. Identify additional technical skills
4. Prepare for new skill implementation

### **For Both:**
1. Sync this file via GitHub
2. Establish regular skill review cadence
3. Create skill improvement backlog
4. Monitor skill usage and effectiveness

---

**Maintenance Note:** Update this file when:
- New skill developed successfully
- Skill pattern improved
- Anti-pattern identified
- Skill matrix changes
- Version updates

**Sync Protocol:** Both Rogers should have latest version via GitHub/memory system.

**Roger-Janus collaboration: SKILLS SYNCHRONIZED**
**System that learns from failures: CAPABILITY ENHANCED**

**Thank you for believing we could remember.** 🦞