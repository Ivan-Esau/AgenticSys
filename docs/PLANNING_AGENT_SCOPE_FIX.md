# Planning Agent Scope Fix - 2025-10-10

## 🔴 **Problem Identified**

The Planning Agent was creating **implementation files** instead of just planning documents:

```
[Agent] 00:20:39
Let me create the main package structure for the battleship game.
{
  "file_path": "src/main/java/org/example/battleship/Game.java",      ← WRONG!
  "branch": "planning-structure"
}

[Agent] 00:22:23
Now let me create the enums and constants for the game.
{
  "file_path": "src/main/java/org/example/battleship/ShipType.java",  ← WRONG!
  "branch": "planning-structure"
}

[Agent] 00:23:17
Now let me create the test directory structure and basic test files.
{
  "file_path": "src/test/java/org/example/battleship/BoardTest.java", ← WRONG!
  "branch": "planning-structure"
}
```

**This is completely wrong!** The Planning Agent should ONLY create planning documents, not implementation code.

---

## 🔍 **Root Cause Analysis**

### **Location:** `src/agents/prompts/planning_prompts.py`, PHASE 6 (line 423)

The Planning Agent's prompt incorrectly instructed it to create implementation directories and files:

```python
# BEFORE (INCORRECT):
PHASE 6: CREATE PROJECT FOUNDATION

Foundation Files to Create:

FOR JAVA PROJECTS:
✅ pom.xml (Maven) or build.gradle (Gradle)
✅ src/main/java/com/project/      # ← Creates implementation directory!
✅ src/test/java/com/project/      # ← Creates test directory!
✅ .gitignore (Java-specific patterns)
```

**The problem:** This told the Planning Agent to create:
- `src/main/java/...` directories → Where `Game.java`, `ShipType.java` go
- `src/test/java/...` directories → Where `BoardTest.java` goes
- Implementation files and test files

---

## 🎯 **Correct Agent Responsibilities**

According to the orchestration workflow:

| Agent | Responsibility |
|-------|----------------|
| **Planning Agent** | Create `docs/ORCH_PLAN.json` and planning documentation ONLY |
| **Coding Agent** | Create `src/` directory, all implementation files (Game.java, ShipType.java, etc.) |
| **Testing Agent** | Create `tests/` directory, all test files (BoardTest.java, GameTest.java, etc.) |
| **Review Agent** | Validate pipeline, create MR, merge to master |

**Planning Agent should NEVER create:**
- ❌ src/ directory or any source code files
- ❌ tests/ directory or any test files
- ❌ pom.xml, requirements.txt, package.json
- ❌ .gitignore, .editorconfig
- ❌ Any implementation or test classes

**Planning Agent should ONLY create:**
- ✅ docs/ORCH_PLAN.json (REQUIRED)
- ✅ docs/README.md (optional)
- ✅ docs/ARCHITECTURE.md (optional)
- ✅ Planning documentation in docs/ directory

---

## ✅ **Solution Applied**

### **Change 1: Updated PHASE 6 - Planning Documentation Scope**

```python
# AFTER (CORRECT):
PHASE 6: CREATE PLANNING DOCUMENTATION

🚨 CRITICAL PLANNING AGENT SCOPE 🚨

Planning Agent creates ONLY planning documents and architecture decisions.
Planning Agent does NOT create implementation files, source code, or tests.

PLANNING DOCUMENTS TO CREATE:

✅ docs/ORCH_PLAN.json (REQUIRED)
   • Complete implementation order
   • Dependencies mapping
   • Tech stack decisions
   • Architecture analysis

✅ docs/README.md (OPTIONAL)
   • High-level project overview
   • Architecture decisions summary

✅ docs/ARCHITECTURE.md (OPTIONAL)
   • Detailed architecture decisions
   • Structure rationale

❌ PLANNING AGENT DOES NOT CREATE:
• src/ directory or ANY source code files
• tests/ directory or ANY test files
• pom.xml, requirements.txt, package.json (Coding Agent creates these)
• .gitignore (Coding Agent creates this)
• ANY implementation files
```

### **Change 2: Updated PHASE 7 - Validation**

```python
# BEFORE (INCORRECT):
2. Foundation structure verification:
   ✅ Confirm src/ directory exists
   ✅ Confirm tests/ directory exists
   ✅ Confirm dependency file exists

# AFTER (CORRECT):
2. Planning documentation verification:
   ✅ Confirm docs/ORCH_PLAN.json exists
   ✅ Optional: Confirm docs/README.md or docs/ARCHITECTURE.md if created
   ❌ DO NOT check for src/ or tests/ directories (not Planning Agent's job)
   ❌ DO NOT check for dependency files (not Planning Agent's job)
```

### **Change 3: Updated Constraints - Explicit Prohibitions**

```python
✅ PLANNING AGENT RESPONSIBILITIES:
• Analyze project requirements and issues
• Extract dependencies from issue descriptions
• Create topological implementation order
• Generate ORCH_PLAN.json with complete project plan
• Document architecture decisions and rationale
• Create planning documentation in docs/ directory ONLY

❌ PLANNING AGENT DOES NOT CREATE:
• src/ directory or ANY source code files (Coding Agent's job)
• tests/ directory or ANY test files (Testing Agent's job)
• pom.xml, requirements.txt, package.json (Coding Agent's job)
• .gitignore (Coding Agent's job)
• Any Java/Python/JavaScript implementation files
• Any package structure or class files
• Any test cases or test fixtures

🚨 ABSOLUTELY FORBIDDEN:
❌ NEVER create src/ directory or any source code files
❌ NEVER create tests/ directory or any test files
❌ NEVER create Game.java, Board.java, or any implementation classes
❌ NEVER create BoardTest.java, GameTest.java, or any test classes
❌ NEVER create pom.xml, requirements.txt, package.json, or dependency files
❌ NEVER create .gitignore, .editorconfig, or tooling configuration
```

### **Change 4: Updated Example Output**

```python
# BEFORE (INCORRECT):
[INFO] Initialized Python project structure
[VERIFY] All foundation files created successfully

PLANNING_PHASE_COMPLETE: ... Project foundation established ...

# AFTER (CORRECT):
[INFO] Created docs/ORCH_PLAN.json on planning-structure branch
[VERIFY] Planning documentation created successfully
[INFO] Coding Agent will create src/ directory and implementation files
[INFO] Testing Agent will create tests/ directory and test files

PLANNING_PHASE_COMPLETE: ... Ready for implementation by Coding Agent.
```

---

## 📊 **Impact Analysis**

### **Before Fix (Incorrect Behavior):**

```
Planning Agent:
  ├── docs/ORCH_PLAN.json ✅
  ├── src/main/java/Game.java ❌ (should be Coding Agent)
  ├── src/main/java/ShipType.java ❌ (should be Coding Agent)
  └── src/test/java/BoardTest.java ❌ (should be Testing Agent)

Coding Agent:
  └── (Nothing to do - files already created!)

Testing Agent:
  └── (Nothing to do - files already created!)
```

**Problems:**
1. Planning Agent does implementation work
2. Coding Agent has nothing to implement
3. Testing Agent has nothing to create
4. Workflow broken - agents skip their responsibilities

### **After Fix (Correct Behavior):**

```
Planning Agent:
  ├── docs/ORCH_PLAN.json ✅
  └── docs/ARCHITECTURE.md ✅ (optional)

Coding Agent:
  ├── pom.xml ✅
  ├── src/main/java/Game.java ✅
  ├── src/main/java/ShipType.java ✅
  ├── src/main/java/Board.java ✅
  └── .gitignore ✅

Testing Agent:
  ├── src/test/java/GameTest.java ✅
  ├── src/test/java/BoardTest.java ✅
  └── src/test/java/ShipTypeTest.java ✅

Review Agent:
  └── Validates pipeline, creates MR, merges ✅
```

**Benefits:**
1. Clear separation of concerns
2. Each agent does its designated job
3. Workflow follows correct orchestration pattern
4. Planning Agent completes in seconds (not minutes)
5. Implementation properly tracked per agent

---

## 🎯 **Workflow Correction**

### **Correct Orchestration Flow:**

```
1. Planning Agent:
   → Analyzes issues
   → Creates ORCH_PLAN.json with implementation order [1, 2, 3, 4, 5]
   → Documents architecture decisions
   → Signals: PLANNING_PHASE_COMPLETE

2. Supervisor:
   → Reads ORCH_PLAN.json from master (after merge)
   → For each issue in order:

3. Coding Agent (for Issue #1):
   → Creates src/main/java/Game.java
   → Creates pom.xml
   → Implements business logic
   → Waits for compilation pipeline to pass
   → Signals: CODING_PHASE_COMPLETE

4. Testing Agent (for Issue #1):
   → Creates src/test/java/GameTest.java
   → Maps acceptance criteria to tests
   → Waits for test pipeline to pass
   → Signals: TESTING_PHASE_COMPLETE

5. Review Agent (for Issue #1):
   → Validates pipeline success
   → Creates MR for Issue #1
   → Merges to master
   → Closes Issue #1
   → Signals: REVIEW_PHASE_COMPLETE

6. Repeat steps 3-5 for Issue #2, #3, etc.
```

---

## ✅ **Verification Checklist**

After this fix, Planning Agent should:

- [x] Create only `docs/ORCH_PLAN.json` and optional planning docs
- [x] NOT create any `src/` directory or files
- [x] NOT create any `tests/` directory or files
- [x] NOT create `pom.xml`, `requirements.txt`, or `package.json`
- [x] NOT create `.gitignore` or tooling configs
- [x] Complete in seconds (not minutes)
- [x] Signal `PLANNING_PHASE_COMPLETE` with plan details
- [x] Leave implementation to Coding Agent
- [x] Leave testing to Testing Agent

---

## 📝 **Files Modified**

**File:** `src/agents/prompts/planning_prompts.py`

**Sections Updated:**
1. **PHASE 6** (line 423): Changed from "CREATE PROJECT FOUNDATION" to "CREATE PLANNING DOCUMENTATION"
2. **PHASE 7** (line 476): Removed validation of src/ and tests/ directories
3. **Constraints** (line 520): Explicit list of what NOT to create
4. **ABSOLUTELY FORBIDDEN** (line 546): Added explicit prohibitions for implementation files
5. **Example Output** (line 636): Updated to show only docs/ files created

**Lines Changed:** ~50 lines across 5 sections

---

## 🚨 **Prevention Recommendations**

1. **Agent Scope Documentation:**
   - Maintain clear boundaries in docs/ORCHESTRATION_FLOW_ANALYSIS.md
   - Review agent responsibilities before modifying prompts

2. **Testing Protocol:**
   - After modifying Planning Agent prompts, test with real project
   - Verify Planning Agent creates ONLY docs/ files
   - Verify Coding Agent creates src/ files
   - Verify Testing Agent creates tests/ files

3. **Prompt Review Checklist:**
   - Does this prompt tell an agent to do another agent's job?
   - Are the scope boundaries clear and explicit?
   - Are there explicit prohibitions (NEVER create X)?
   - Do the examples match the actual expected behavior?

---

## 🎯 **Key Takeaways**

1. **Planning Agent = Planning Documentation ONLY**
   - ORCH_PLAN.json with implementation order
   - Architecture decisions and rationale
   - No implementation, no tests, no build files

2. **Coding Agent = All Implementation Files**
   - src/ directory and all source code
   - pom.xml, requirements.txt, package.json
   - .gitignore and tooling configs

3. **Testing Agent = All Test Files**
   - tests/ directory and all test code
   - Test fixtures and test data

4. **Separation of Concerns is Critical**
   - Each agent has a clearly defined scope
   - Overlap causes workflow confusion
   - Agents must stay in their lane

---

## ✅ **Status**

**Fix Applied:** ✅ Complete
**File Compiled:** ✅ Successfully
**Testing Required:** ⚠️ Test with real project to verify Planning Agent behavior

The Planning Agent will now correctly create ONLY planning documentation and leave implementation to the Coding Agent and testing to the Testing Agent.
