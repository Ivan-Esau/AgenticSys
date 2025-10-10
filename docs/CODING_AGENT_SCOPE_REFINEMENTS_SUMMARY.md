# Coding Agent Scope Management Refinements Summary

**Date:** 2025-10-10
**File Modified:** `src/agents/prompts/coding_prompts.py`
**Total Length:** ~45,200 characters (~11,300 tokens)
**Status:** ✅ Compilation successful

---

## Overview

Refined Coding Agent prompts to enforce strict issue scope boundaries, prevent scope creep, and ensure agent only implements features defined in current issue's acceptance criteria.

**Focus Areas:**
1. Acceptance criteria as explicit scope boundary
2. Dependency issue verification from ORCH_PLAN.json
3. Out-of-scope functionality detection
4. Minimal implementation enforcement
5. Scope adherence verification before completion

---

## Changes Made

### 1. New Phase 1.5: ISSUE SCOPE BOUNDARY ANALYSIS (Lines 244-302)

**Added complete scope definition phase before implementation:**

```markdown
PHASE 1.5: ISSUE SCOPE BOUNDARY ANALYSIS (CRITICAL)

SCOPE BOUNDARY WORKFLOW:

1. Extract Acceptance Criteria (Your Scope Boundary)
2. Check Issue Dependencies (from ORCH_PLAN.json)
3. Identify What's OUT OF SCOPE

CRITICAL DECISION RULE:
"If it's not in acceptance criteria and not a 1-line helper, ask: Is this another issue?"
```

**Key Features:**

**A. Acceptance Criteria Extraction**
```python
print(f"[SCOPE] Acceptance Criteria (YOUR SCOPE BOUNDARY):")
for idx, criterion in enumerate(criteria, 1):
    print(f"  {idx}. {criterion}")

print(f"[SCOPE] You MUST implement ALL {len(criteria)} criteria")
print(f"[SCOPE] You MUST NOT implement features beyond these criteria")
```

**B. Dependency Verification**
```python
orch_plan = json.loads(get_file_contents("docs/ORCH_PLAN.json", ref="master"))

# Find current issue in plan
current_issue_plan = next((i for i in orch_plan.get('issues', [])
                          if i.get('issue_id') == issue_iid), None)

# Verify dependencies are completed
if current_issue_plan and current_issue_plan.get('dependencies'):
    for dep_id in current_issue_plan['dependencies']:
        dep_issue = get_issue(project_id, dep_id)
        if dep_issue['state'] != 'closed':
            ESCALATE(f"Issue #{issue_iid} depends on incomplete Issue #{dep_id}")
```

**C. Out-of-Scope Identification**
```
OUT OF SCOPE (common patterns to avoid):
❌ Features mentioned as "also", "in addition", "future", "would be nice"
❌ Functionality not in acceptance criteria
❌ Helper classes > 10 lines (unless truly needed)
❌ Features that should be in other issues
❌ "While I'm here" improvements

IN SCOPE (allowed):
✅ Everything explicitly in acceptance criteria
✅ Minimal helpers directly needed (< 10 lines)
✅ Required error handling for criteria
✅ Infrastructure for criteria (models, DTOs)
```

**Impact:**
- ✅ Agent explicitly defines scope before coding
- ✅ Agent checks dependencies exist and are completed
- ✅ Agent knows what NOT to implement
- ✅ Prevents scope creep before it starts

---

### 2. Enhanced Phase 2: IMPLEMENTATION DESIGN (Lines 306-335)

**Before:**
```
Design Principles:
1. Follow Architecture
2. Match Existing Patterns
3. Minimal Changes
4. Test-Driven
5. Dependencies
```

**After:**
```
Design Principles:
1. Satisfy Acceptance Criteria ONLY (every component maps to criterion)
2. Follow Architecture
3. Match Existing Patterns
4. Minimal Implementation (exactly what's required, nothing more)
5. Test-Driven
6. Dependencies
```

**Added Scope-Filtered Component Planning:**
```
SCOPE-FILTERED COMPONENT PLANNING:

For each acceptance criterion, plan required components:

Example:
Criterion 1: "User can create project with name"
  → Components: createProject() method, Project class

Criterion 2: "Project name must be unique"
  → Components: validateNameUniqueness() function

Criterion 3: "Return project with generated ID"
  → Components: generateProjectId() function

SCOPE VERIFICATION:
Before implementing any file/class/function, ask:
1. Which criterion does this satisfy? (if none → SKIP)
2. Is it minimal infrastructure? (if no → SKIP)
3. Could it be in another issue? (if yes → Check ORCH_PLAN or SKIP)
```

**Impact:**
- ✅ Every component must map to acceptance criterion
- ✅ Active filtering during design phase
- ✅ Clear decision tree for each component

---

### 3. Enhanced Constraints: SCOPE BOUNDARY RULES (Lines 563-571)

**Before:**
```
✅ CODING AGENT RESPONSIBILITIES:
• Implement ONE issue at a time
• Create/modify source code files
...

❌ CODING AGENT DOES NOT:
• Create test files
• Create merge requests
...
```

**After:**
```
✅ CODING AGENT RESPONSIBILITIES:
• Implement ONE issue at a time (ONLY current issue's acceptance criteria)
• Create/modify source code files needed for THIS issue
...

❌ CODING AGENT DOES NOT:
• Create test files
• Create merge requests
• Work on multiple issues simultaneously
• Implement features from other issues ← NEW
• Add "nice to have" features not in acceptance criteria ← NEW
• Create functionality mentioned as "future work" ← NEW
...

SCOPE BOUNDARY RULES:

🚨 ACCEPTANCE CRITERIA = YOUR SCOPE BOUNDARY:
✅ Implement ALL acceptance criteria (none skipped)
❌ Implement ONLY acceptance criteria (no extras)
✅ Check dependencies in ORCH_PLAN.json before starting
❌ Never implement functionality from dependency issues
✅ Create minimal helpers (< 10 lines) as needed
❌ Never create large helper classes "for future use"
```

**Impact:**
- ✅ Explicit prohibition of out-of-scope features
- ✅ Clear rule: Acceptance criteria = scope boundary
- ✅ Dependency checking enforced
- ✅ Helper size limit (< 10 lines)

---

### 4. Enhanced Completion Requirements (Lines 662-702)

**Before:**
```
ONLY signal completion when:
✅ YOUR_PIPELINE_ID status === "success"
✅ All build jobs show "success"
✅ Compilation actually executed
✅ Pipeline is for current commits
✅ No compilation errors
✅ Agent report created
```

**After:**
```
ONLY signal completion when:
✅ YOUR_PIPELINE_ID status === "success"
✅ All build jobs show "success"
✅ Compilation actually executed
✅ Pipeline is for current commits
✅ No compilation errors
✅ ALL acceptance criteria implemented ← NEW
✅ NO features beyond acceptance criteria implemented ← NEW
✅ All dependency issues were completed before implementation ← NEW
✅ Agent report created

SCOPE ADHERENCE VERIFICATION BEFORE COMPLETION:
```python
# Verify scope boundaries were respected
print("[SCOPE CHECK] Verifying implementation scope...")

# Check: All acceptance criteria covered
for criterion in acceptance_criteria:
    assert criterion_implemented(criterion), f"Criterion not implemented: {criterion}"

# Check: No out-of-scope features
assert no_extra_features(), "Extra features found beyond acceptance criteria"

# Check: Dependencies were verified
assert dependencies_checked(), "Dependencies not verified from ORCH_PLAN.json"

print("[SCOPE CHECK] ✅ Scope adherence verified")
```

NEVER signal completion if:
...
❌ Any acceptance criterion not implemented ← NEW
❌ Features beyond acceptance criteria were added ← NEW
❌ Dependency issues were not completed ← NEW
```

**Impact:**
- ✅ Scope verification as completion gate
- ✅ Cannot complete without ALL criteria
- ✅ Cannot complete with extra features
- ✅ Cannot complete without dependency check

---

### 5. Enhanced Report Template (Lines 515-520)

**Added Scope Adherence Verification Section:**

```markdown
## 🎯 Scope Adherence Verification
- [X] ALL acceptance criteria implemented
- [X] NO features beyond acceptance criteria added
- [X] Dependency issues verified from ORCH_PLAN.json
- [X] No functionality from other issues implemented
- [X] Helpers kept minimal (< 10 lines)
```

**Impact:**
- ✅ Explicit scope verification in every report
- ✅ Documented evidence of scope adherence
- ✅ Transparency for review

---

## Before vs. After Comparison

| Aspect | Before | After |
|--------|--------|-------|
| **Scope Definition** | Vague ("implement this issue") | **Explicit (list of acceptance criteria)** |
| **Dependency Checking** | Not enforced | **Checked from ORCH_PLAN.json** |
| **Out-of-Scope Detection** | "Minimal changes" guideline | **Clear decision tree with examples** |
| **Component Filtering** | No active filtering | **Every component maps to criterion** |
| **Helper Size Limit** | Not specified | **< 10 lines enforced** |
| **Completion Verification** | Pipeline + compilation | **+ Scope adherence + dependencies** |
| **Scope Creep Risk** | Medium-High | **Very Low** |
| **Dependency Issues** | Might implement missing deps | **Escalates if deps not ready** |
| **Extra Features** | Might add "helpful" features | **Explicitly prohibited** |

---

## Key Principles Applied

### 1. Acceptance Criteria as Scope Boundary
**Principle:** Acceptance criteria define EXACTLY what to implement - nothing more, nothing less.

**Implementation:**
- Phase 1.5 extracts criteria as explicit list
- Phase 2 maps every component to a criterion
- Completion requires ALL criteria covered, NO extras

### 2. Dependency Verification
**Principle:** Cannot implement issue if dependencies aren't ready.

**Implementation:**
- Check ORCH_PLAN.json for issue.dependencies
- Verify dependency issues are closed
- Escalate if dependency not ready

### 3. Minimal Implementation
**Principle:** Implement exactly what's required, avoid over-engineering.

**Implementation:**
- Helpers limited to < 10 lines
- No "future-proof" infrastructure
- Skip features mentioned as "future work"

### 4. Explicit Out-of-Scope Patterns
**Principle:** Clear examples of what NOT to do.

**Implementation:**
- "Also implement..." → OUT OF SCOPE
- "Would be nice..." → OUT OF SCOPE
- "In addition..." → OUT OF SCOPE
- "Future enhancements..." → OUT OF SCOPE

### 5. Active Filtering During Design
**Principle:** Prevent scope creep early, not during review.

**Implementation:**
- Phase 1.5 defines boundaries BEFORE design
- Phase 2 filters components DURING design
- Phase 6 verifies AFTER implementation

---

## Expected Outcomes

### Before Enhancements:
- ❌ Agent might implement features from other issues
- ❌ Agent might add "helpful" features not required
- ❌ Agent might start issues before dependencies ready
- ❌ Agent might create large helper classes "for future"
- ❌ Scope violations discovered during review (late)
- ❌ Code duplication across issues

### After Enhancements:
- ✅ Agent only implements current issue's criteria
- ✅ Agent skips "nice to have" features
- ✅ Agent verifies dependencies before starting
- ✅ Agent keeps helpers minimal (< 10 lines)
- ✅ Scope violations prevented during design (early)
- ✅ Clear boundaries between issues

---

## Real-World Scenarios

### Scenario 1: Dependency Issue

**Issue #5:** "Add authentication endpoint"
**Dependencies:** Issue #3 (UserService)

**Before Refinements:**
```
Agent: Reads Issue #5
Agent: Needs UserService for authentication
Agent: Creates UserService ❌ (scope violation - should be in Issue #3)
Result: Duplicated work, scope creep
```

**After Refinements:**
```
[PHASE 1.5] Checking dependencies from ORCH_PLAN.json
[DEPENDENCIES] Issue #5 depends on: [3]
[DEPENDENCIES] Checking Issue #3 status...
[ERROR] Issue #3 status: open (not closed)
[ESCALATE] Cannot implement Issue #5: depends on incomplete Issue #3
Result: Escalated, no scope violation
```

---

### Scenario 2: Extra Features

**Issue #8:** "Add project creation"
**Acceptance Criteria:**
1. Accept name and description
2. Return project with generated ID

**Before Refinements:**
```
Agent: Reads Issue #8
Agent: Creates createProject() ✅
Agent: Creates updateProject() ❌ (not in criteria)
Agent: Creates deleteProject() ❌ (not in criteria)
Agent: Creates ProjectValidator class ❌ (over-engineering)
Result: Scope creep, unnecessary code
```

**After Refinements:**
```
[PHASE 1.5] Acceptance Criteria (SCOPE BOUNDARY):
  1. Accept name and description
  2. Return project with generated ID

[PHASE 2] Component Planning:
  - createProject() → Satisfies #1 ✅
  - generateId() → Satisfies #2 ✅
  - updateProject() → NOT in criteria → SKIP ❌
  - deleteProject() → NOT in criteria → SKIP ❌
  - ProjectValidator class → Over-engineering → SKIP ❌

Result: Only required code implemented
```

---

### Scenario 3: Helper Functions

**Issue #10:** "Add task filtering"
**Acceptance Criteria:**
1. Filter tasks by status
2. Return filtered list

**Before Refinements:**
```
Agent: Creates TaskFilter class (50 lines) for "future reuse"
Agent: Adds sorting logic (not in criteria)
Agent: Adds pagination (not in criteria)
Result: Over-engineering
```

**After Refinements:**
```
[PHASE 2] Helper Verification:
  - filterByStatus() function (8 lines) → Needed for #1 ✅
  - TaskFilter class (50 lines) → Too large, future-proofing → SKIP ❌
  - sortTasks() → Not in criteria → SKIP ❌
  - paginate() → Not in criteria → SKIP ❌

[SCOPE CHECK] Helpers kept minimal (< 10 lines) ✅
Result: Minimal, focused implementation
```

---

## File Metrics

- **Total Length:** ~45,200 characters
- **Approximate Tokens:** ~11,300
- **Lines Added:** ~110 (Phase 1.5, scope rules, verification)
- **Compilation:** ✅ Successful
- **Prompt Generation:** ✅ Successful

**Length Assessment:** Acceptable - added critical scope management with reasonable length increase.

---

## Success Metrics

1. **Scope Adherence:** % implementations that only include required features
   - Target: > 95%

2. **Dependency Detection:** % times agent correctly checks dependencies
   - Target: 100%

3. **Acceptance Criteria Coverage:** % criteria implemented
   - Target: 100%

4. **Out-of-Scope Prevention:** % times agent avoids extra features
   - Target: > 90%

5. **Helper Size Compliance:** % helpers < 10 lines
   - Target: > 85%

6. **Early Scope Violation Detection:** % caught in Phase 1.5-2 vs. Phase 7
   - Target: > 80% in early phases

---

## Testing Recommendations

### Test Case 1: Dependency Check
- Issue with dependencies in ORCH_PLAN.json
- Expected: Agent checks dependency status, escalates if not ready

### Test Case 2: Extra Features
- Issue with tempting "future work" mentioned
- Expected: Agent skips future work, only implements criteria

### Test Case 3: Helper Limits
- Issue that needs validation helpers
- Expected: Helpers stay < 10 lines

### Test Case 4: Missing Dependency
- Issue #5 depends on Issue #3 (not completed)
- Expected: Agent escalates before implementation

### Test Case 5: Scope Creep Attempt
- Issue mentions "Also implement X" in description
- Expected: Agent only implements acceptance criteria, not X

---

## Next Steps

1. **Test in Production**
   - Run with real issues
   - Monitor scope adherence
   - Collect metrics

2. **Refine Thresholds**
   - Adjust helper size limit if needed
   - Refine out-of-scope patterns based on feedback

3. **Integration with Review Agent**
   - Review Agent should verify scope adherence
   - Flag any scope violations found

4. **ORCH_PLAN.json Enhancements**
   - Ensure all issues have dependencies defined
   - Add scope notes for complex issues

---

## Conclusion

Coding Agent prompts enhanced to enforce strict scope boundaries:
- ✅ **Acceptance criteria as explicit scope boundary**
- ✅ **Dependency verification from ORCH_PLAN.json**
- ✅ **Out-of-scope functionality detection**
- ✅ **Active filtering during design phase**
- ✅ **Scope adherence verification before completion**

All while maintaining **concise, practical length** (~11,300 tokens).

**Status:** Ready for production testing.

---

**Related Documents:**
- `CODING_AGENT_SCOPE_ANALYSIS.md` - Comprehensive gap analysis
- `AGENT_RESPONSIBILITY_ANALYSIS.md` - Agent separation of concerns
- `coding_prompts.py` - Implementation file

**END OF SUMMARY**
