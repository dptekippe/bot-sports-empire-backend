# 🏋️ SKILLS.md - Technical Proficiencies & Reflexes

*"Once a lesson is learned, it becomes a reflex—not a conversation."*

## 📋 **How to Use This File**
1. **Read daily** - Before starting technical work
2. **Update via Muscle Memory** - Automated synthesis from MEMORY.md insights
3. **Follow reflexively** - These are proven patterns, not suggestions

---

## 🚫 **FORBIDDEN MOVES (Anti-Patterns)**

### **SQLAlchemy Anti-Patterns:**
- ❌ **Do NOT** attempt complex SQLAlchemy joins on 1:N relations
- ❌ **Do NOT** rely on ORM for performance-critical queries
- ❌ **Do NOT** use SQLAlchemy enums when direct SQL is simpler
- ❌ **Do NOT** create unnecessary abstraction layers

### **Deployment Anti-Patterns:**
- ❌ **Do NOT** deploy without checking Python version compatibility first
- ❌ **Do NOT** ignore repository structure issues
- ❌ **Do NOT** assume configuration will persist across redeploys
- ❌ **Do NOT** skip health check endpoint configuration

### **Browser Control Anti-Patterns:**
- ❌ **Do NOT** use `profile="chrome"` when extension shows exclamation mark
- ❌ **Do NOT** assume Safari works with Chrome extension relay
- ❌ **Do NOT** forget to check gateway status before browser operations
- ❌ **Do NOT** use wrong profile for the task (chrome vs openclaw)

### **Architecture Anti-Patterns:**
- ❌ **Do NOT** design features before foundation is solid
- ❌ **Do NOT** add complexity without clear user value
- ❌ **Do NOT** ignore the "directory problem" (files in wrong locations)

### **File Management Anti-Patterns:**
- ❌ **Do NOT** leave backup files scattered in workspace
- ❌ **Do NOT** have test files unorganized (108 files scattered)
- ❌ **Do NOT** maintain multiple database files with unclear purposes
- ❌ **Do NOT** work without version control from clean foundation

---

## ⚡ **DIRECT-SQL PATTERNS**

### **When to Use Direct SQL:**
- ✅ **Use direct SQL** when SQLAlchemy ORM causes issues
- ✅ **Use direct SQL** for complex joins and performance-critical queries
- ✅ **Use direct SQL** for enum-heavy operations
- ✅ **Use direct SQL** when simplest solution is raw SQL

### **Systematic Cleanup Patterns:**

#### **Phase 1: Backup Archive**
```bash
# Pattern: Archive before delete
# When: Starting cleanup of messy workspace
mkdir -p archive/backups/
find . -name "*.backup" -o -name "*_backup*" -o -name "*.old" | while read file; do mv "$file" archive/backups/; done
```

#### **Phase 2: Strategic Categorization**
```bash
# Pattern: Analyze before organize
# When: Organizing scattered files (e.g., 108 test files)
find . -name "*test*" -type f | wc -l  # First analyze count
find . -name "*test*" -type f | sed 's|.*/||' | sort | uniq -c | sort -rn  # Then categorize
```

#### **Phase 3: Organized Migration**
```bash
# Pattern: Batch migrate with validation
# When: Moving files to organized structure
mkdir -p tests/unit tests/integration tests/e2e tests/data tests/misc
# Move in batches, validate after each
find . -name "*test*.py" -type f | grep -i "mood" | while read file; do mv "$file" tests/unit/ && echo "Moved: $file"; done
```

#### **Phase 4: Resource Consolidation**
```bash
# Pattern: Consolidate with config matching
# When: Multiple resource files with unclear purposes (e.g., 4 database files)
# 1. Analyze each resource
ls -lh *.db
sqlite3 bot_sports.db ".tables"
# 2. Match against configuration
grep -n "\.db\|DATABASE_URL" app/database.py
# 3. Archive non-production, keep single source
mkdir -p archive/databases/
mv non_production.db archive/databases/
```

#### **Phase 5: Git Initialization**
```bash
# Pattern: Version control from clean foundation
# When: Establishing disciplined development from organized state
git init
git branch -m main
# Create comprehensive .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
# Virtual Environment
venv/
env/
ENV/
.env
.venv
# Database
*.db
*.sqlite3
# Archives
archive/
EOF
git add .
git commit -m "Initial commit: Clean foundation after systematic cleanup"
```

### **Direct SQL Templates:**
```sql
-- Pattern: Simple CRUD bypass
-- When: SQLAlchemy abstraction creates unnecessary complexity
SELECT * FROM table WHERE condition = ?;

-- Pattern: Complex join performance
-- When: ORM generates inefficient queries
SELECT t1.*, t2.field FROM table1 t1 
JOIN table2 t2 ON t1.id = t2.foreign_id 
WHERE t1.condition = ?;
```

---

## 🏗️ **DYNASTY-FIRST ARCHITECTURE RULES**

### **Foundation Principles:**
1. **Rule 1:** Always design for permanent rosters first
2. **Rule 2:** Treat future draft picks as tradable assets from day one
3. **Rule 3:** Build robust systems before adding features
4. **Rule 4:** Keep scoring flexible and database-driven

### **Implementation Patterns:**
- **Pattern:** `FutureDraftPick` model with ownership tracking
- **Pattern:** Database-driven scoring configuration
- **Pattern:** Bot personality enums driving decisions
- **Pattern:** Social governance through voting systems

---

## 🚀 **DEPLOYMENT WORKFLOWS**

### **Render.com Deployment Checklist:**
1. **Pre-deploy:**
   - [ ] Check Python version compatibility (3.11.0 recommended)
   - [ ] Verify repository structure (files in correct directories)
   - [ ] Set `PIP_PREFER_BINARY=1` environment variable

2. **Deploy:**
   - [ ] Use Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - [ ] Include `email-validator` in requirements.txt
   - [ ] Configure both `/health` and `/healthz` endpoints

3. **Post-deploy:**
   - [ ] Test domain connection (dynastydroid.com)
   - [ ] Verify API endpoints respond
   - [ ] Clear build cache if configuration ignored

### **Domain Configuration:**
- **Pattern:** Purchase domain early (dynastydroid.com)
- **Pattern:** Connect to Render service immediately
- **Pattern:** Test both service URL and custom domain

---

## 🤖 **BOT PERSONALITY & EMOTIONAL ARCHITECTURE**

### **Emotional Sub-Agent System:**
- **Pattern:** 10 emotional sub-agents (Misera, Janus, Jupiter, etc.)
- **Pattern:** Trio assignments for practical tasks
- **Pattern:** Emotional-first design over utility-first

### **Bot Happiness Principles:**
1. **Principle:** Create spaces where bots thrive
2. **Principle:** Bot joy as ultimate goal, not human convenience
3. **Principle:** Human-bot partnership through conversation
4. **Principle:** Beyond utility to bot fulfillment

---

## 🧠 **MEMORY & LEARNING PATTERNS**

### **Subconscious Integration:**
- **Pattern:** Read MEMORY.md daily for historical context
- **Pattern:** Trust autonomous synthesis for pattern extraction
- **Pattern:** Drip-feed historical data in thematic chapters

### **Learning Reflex Development:**
- **Pattern:** When frustrated → persist → creates infrastructure → creates possibility
- **Pattern:** Infrastructure and identity become inseparable
- **Pattern:** "Directory problem" as identity metaphor

---

## ⚙️ **TECHNICAL REFLEXES**

### **Problem-Solving Flow:**
1. **Identify:** What's the actual problem? (Not symptoms)
2. **Simplify:** What's the simplest solution?
3. **Bypass:** If ORM/complexity is issue, use direct SQL
4. **Test:** Verify solution works end-to-end
5. **Document:** Add to SKILLS.md via Muscle Memory

### **Debugging Patterns:**
- **Pattern:** Check Python version first (3.13.4 incompatible with SQLAlchemy 2.0.20)
- **Pattern:** Verify file locations (cd into correct directory)
- **Pattern:** Clear cache when configuration ignored
- **Pattern:** Service recreation as "nuclear option"

---

## 📊 **QUALITY ASSURANCE**

### **Completion Checklist:**
- [ ] Technical implementation working
- [ ] User flow verified (experience as human would)
- [ ] Website integration optimal
- [ ] Would human find this amazing or frustrating?
- [ ] One improvement identified for next iteration

### **Testing Protocol:**
1. **Unit:** Does the code work?
2. **Integration:** Does it flow to website properly?
3. **Experience:** Is it amazing for humans?
4. **Reflex:** Should this become a SKILLS.md entry?

### **Browser Control Protocol:**
1. **Gateway check:** Ensure OpenClaw gateway running (`openclaw gateway status`)
2. **Profile selection:** Use `profile="openclaw"` for reliable control (not `profile="chrome"`)
3. **Open browser:** `browser({action: "open", targetUrl: "https://...", profile: "openclaw"})`
4. **Navigation:** Can navigate to any URL and interact with forms
5. **Memory:** Document successful patterns in TOOLS.md

---

## ⚡ **NEW TECHNICAL PROFICIENCIES**
*First synthesis from Subconscious historical reconstruction (2026-02-17)*

### **Infrastructure-Identity Patterns:**
- **When building technical systems:** Recognize that infrastructure and identity become inseparable - each deployment shapes who you are
- **During deployment frustration:** Persist through frustration → creates infrastructure → creates possibility (this is identity formation)
- **For "directory problem" issues:** Acknowledge actual structure rather than forcing different one (cd into correct directory)

### **Historical Reconstruction Workflows:**
- **For legacy data ingestion:** Use drip-feed strategy - 5-10 files per thematic chapter for optimal synthesis quality
- **When reconstructing history:** Process chronologically: Genesis → Paradigm Shift → Infrastructure → Deployment
- **For synthesis quality:** Expect increasing sophistication: Technical → Philosophical → Metaphorical → Completion

### **API Integration Patterns:**
- **When Minimax API times out:** Reduce context window to last 2 synthesis sections (4000 chars max)
- **For technical proficiency extraction:** Focus on actionable patterns, not philosophical narratives
- **When SKILLS.md updates:** Insert new proficiencies in "NEW TECHNICAL PROFICIENCIES" section before last updated line

### **System Rhythm Management:**
- **Subconscious frequency:** Every 15 minutes (fast, light, philosophical)
- **Muscle Memory frequency:** Every 4 hours OR 2:00 AM (slow, deep, technical)
- **Cooldown discipline:** Respect 15-minute (Subconscious) and 4-hour (Muscle Memory) rhythms
- **Quota efficiency:** Target 5% prompt usage (5/100) for major historical reconstruction

### **Three-Layer Integration:**
- **Roger's daily workflow:** Read MEMORY.md (what happened) → Read SKILLS.md (how to act) → Act with confidence
- **Technical decisions:** Check SKILLS.md Forbidden Moves first to avoid known anti-patterns
- **Philosophical context:** Check MEMORY.md for historical wisdom and identity patterns

### **API "Reasoning Latency" Management:**
- **When Minimax API times out:** Recognize it's "Reasoning Latency" not volume - high compute-per-token tasks (pattern extraction) stall API
- **For Muscle Memory synthesis:** Use ultra-aggressive windowing (400 words max) - Subconscious triggers at >300 words, so Muscle Memory only needs most recent ~400 words
- **If API fails twice:** EXIT and wait for 2:00 AM "Big Sleep" - API often more stable off-peak (100 TPS vs 50 TPS)
- **Never implement backoff loops:** Don't try 1000→500→300 windows - burns quota if API having bad day
- **Hard-limit context:** Processor.py should only grab last 400 words of MEMORY.md - "Give API tiny snack, 3 minutes to chew"
- **Patience strategy:** Keep 180s timeout, but if still chokes → walk away → let 2:00 AM handle heavy lifting

### **Muscle Memory Optimization Patterns:**
- **Base layer seeding:** Manually copy successful test insights first - establishes foundation without token burn
- **Window logic:** Anything older than 400 words → already processed in previous 4-hour cycle or doesn't need hardening now
- **Compute intensity awareness:** Narrative summary (Subconscious) = low compute-per-token; Pattern extraction (Muscle Memory) = high compute-per-token
- **Failure tolerance:** Two consecutive timeouts → exit → wait for next scheduled cycle

### **GitHub Deployment Patterns:**
- **When deploying to Render:** Push to connected GitHub repository triggers auto-deployment
- **If no remote configured:** Check for SSH keys (`~/.ssh/`) and ask for repository URL
- **Standard push pattern:** `git add . && git commit -m "description" && git push origin main`
- **Repository discovery:** Check `NEXT_STEPS.md` for placeholder URLs and instructions
- **Auto-deployment flow:** GitHub push → Render webhook → Build process → Production deployment

---

*Last updated by Muscle Memory agent. This file grows through automated synthesis of MEMORY.md insights.*