# Coding Agent Scope Management Analysis

**Date:** 2025-10-10
**Version:** 1.0
**Focus:** Issue scope adherence and boundary detection

---

## Executive Summary

Analysis of Coding Agent prompts reveals **strong foundation but 6 critical gaps** in scope boundary detection, dependency checking, and out-of-scope functionality identification.

**Key Findings:**
- ✅ **Strong:** "Implement ONE issue at a time" directive
- ✅ **Strong:** Acceptance criteria coverage requirements
- ✅ **Strong:** Architecture adherence from ORCH_PLAN.json
- ⚠️ **Gap:** No dependency issue checking before implementation
- ⚠️ **Gap:** No out-of-scope functionality detection
- ⚠️ **Gap:** No guidance on minimal vs. complete implementation
- ⚠️ **Gap:** Acceptance criteria not emphasized as scope boundary
- ⚠️ **Gap:** No check for related/blocked issues
- ⚠️ **Gap:** No guidance on when functionality belongs in another issue

---

## Current Scope Management

### ✅ What Works Well

#### 1. Single Issue Focus (Line 464)
```
✅ CODING AGENT RESPONSIBILITIES:
• Implement ONE issue at a time
```

**Strength:** Clear directive

#### 2. Acceptance Criteria Coverage (Lines 421-430)
```markdown
## 📝 Acceptance Criteria Coverage (from GitLab Issue)
- [X] Criterion 1: {{description}} - Implemented in {{file:line}}
- [X] Criterion 2: {{description}} - Implemented in {{file:line}}
(List ALL acceptance criteria from issue - NONE should be unchecked)
```

**Strength:** All criteria must be covered

#### 3. Minimal Changes Principle (Line 249)
```
3. **Minimal Changes:** Only add what's required for this issue
```

**Strength:** Encourages focused implementation

#### 4. Issue Fetching Required (Lines 216-229)
```
Step 3 - Issue Analysis (MANDATORY - Fetch Full Issue):
• Use get_issue(project_id, issue_iid) → Get COMPLETE requirements
• Parse description for:
  - Acceptance criteria
  - Technical requirements
  - Dependencies
  - Edge cases
```

**Strength:** Gets full issue context

### ⚠️ Critical Gaps

---

## Gap 1: No Dependency Issue Checking

### Current State
Agent fetches current issue but **doesn't check if it depends on other issues**.

### Problem
If Issue #5 depends on Issue #3 (which implements a required service), agent may:
- Try to implement the missing service itself (scope creep)
- Create incomplete/broken code
- Not realize dependency is missing

### Example Scenario
```
Issue #5: "Add user authentication endpoint"
- Requires: UserService (defined in Issue #3)
- Issue #3 status: Open (not implemented yet)

Agent behavior without dep check:
- Reads Issue #5
- Sees it needs UserService
- Creates UserService itself ❌ (should be in Issue #3)
- Scope violation!
```

### Missing Instructions
```
BEFORE implementation:
1. Check ORCH_PLAN.json for issue.dependencies
2. Verify dependency issues are completed
3. If dependency missing:
   - Check if dependency issue exists and is completed
   - If completed: Use existing implementation
   - If not completed: ESCALATE
```

---

## Gap 2: No Out-of-Scope Functionality Detection

### Current State
"Minimal Changes: Only add what's required" is vague - no specific guidance on **identifying** what's required.

### Problem
Agent lacks clear criteria for determining:
- Is this function needed for THIS issue?
- Should this helper class be created now or later?
- Is this feature part of this issue or another one?

### Example Scenarios

**Scenario A: Helper Functions**
```
Issue #7: "Add project creation endpoint"
Acceptance Criteria:
- POST /projects accepts name and description
- Returns created project with ID

During implementation, agent realizes it needs:
- validateProjectName() helper
- generateProjectId() helper
- formatProjectResponse() helper

Questions:
- Which helpers are in scope?
- Which are over-engineering?
- Which might be defined in other issues?

Current prompt: No guidance
```

**Scenario B: Related Features**
```
Issue #10: "Add task editing"
Acceptance Criteria:
- Update task name
- Update task description
- Update task due date

During implementation, agent thinks:
- "Should I also add task deletion?" (No - different issue)
- "Should I add task status update?" (No - different issue)
- "Should I validate due date format?" (Yes - part of editing)

Current prompt: No clear boundary
```

### Missing Instructions
```
SCOPE BOUNDARY DECISION TREE:

For every function/class you consider creating, ask:

1. Is it DIRECTLY needed to satisfy an acceptance criterion?
   - YES → In scope
   - NO → Continue to #2

2. Is it a minimal helper for code in this issue?
   - YES and < 10 lines → In scope
   - YES and > 10 lines → Check if it's reusable

3. Will it be used by future issues?
   - YES → Check ORCH_PLAN.json - is it planned elsewhere?
   - NO → In scope as helper

4. Is it mentioned in issue description/acceptance criteria?
   - YES → In scope
   - NO → OUT OF SCOPE

When in doubt: Implement ONLY what acceptance criteria explicitly require
```

---

## Gap 3: Acceptance Criteria Not Emphasized as Boundary

### Current State
Acceptance criteria are covered in report (Phase 7) but **not used as scope filter** during implementation (Phase 2-3).

### Problem
Agent implements acceptance criteria BUT may also add extra features not required.

### Current Flow
```
Phase 1: Read issue
Phase 2: Design implementation (no scope check)
Phase 3: Create files (no scope check)
Phase 7: Document acceptance criteria coverage
```

**Missing:** Active filtering during design/implementation

### Needed Enhancement
```
Phase 2: IMPLEMENTATION DESIGN

SCOPE BOUNDARY ENFORCEMENT:

BEFORE designing any component, verify it satisfies an acceptance criterion:

For each planned file/class/function:
1. Which acceptance criterion does this satisfy?
2. If none → Is it absolutely required infrastructure?
3. If not required → SKIP IT

Example:
Acceptance Criteria:
  1. User can create project with name
  2. Project must have unique name
  3. Return project ID on creation

Planned components:
✅ createProject(name) → Satisfies #1
✅ validateUniqueName() → Satisfies #2
✅ generateProjectId() → Satisfies #3
❌ updateProject() → NOT in criteria → OUT OF SCOPE
❌ deleteProject() → NOT in criteria → OUT OF SCOPE
❌ ProjectAuditLogger → NOT in criteria → OUT OF SCOPE
```

---

## Gap 4: No ORCH_PLAN.json Dependency Checking

### Current State
Agent reads ORCH_PLAN.json for architecture BUT **doesn't check issue dependencies or implementation order**.

### Problem
ORCH_PLAN.json may contain:
```json
{
  "issues": [
    {
      "issue_id": 3,
      "title": "Implement UserService",
      "dependencies": [],
      "priority": 1
    },
    {
      "issue_id": 5,
      "title": "Add authentication endpoint",
      "dependencies": [3],  // Depends on Issue #3!
      "priority": 2
    }
  ]
}
```

Agent implementing Issue #5 **doesn't check** that Issue #3 must be done first.

### Missing Instructions
```
Phase 1: CONTEXT GATHERING

Step 2.5 - Dependency Verification:

Extract from ORCH_PLAN.json:
1. Find current issue in issues array
2. Check "dependencies" field
3. For each dependency:
   - Verify dependency issue is marked as "completed"
   - If not completed: ESCALATE

Example:
```python
current_issue_iid = 5
orch_plan = get_file_contents("docs/ORCH_PLAN.json", ref="master")
plan_data = json.loads(orch_plan)

# Find current issue
current_issue = next(i for i in plan_data['issues'] if i['issue_id'] == current_issue_iid)

# Check dependencies
if 'dependencies' in current_issue and current_issue['dependencies']:
    for dep_id in current_issue['dependencies']:
        dep_issue = get_issue(project_id, dep_id)
        if dep_issue['state'] != 'closed':
            ESCALATE(f"Issue #{current_issue_iid} depends on Issue #{dep_id} which is not completed (status: {dep_issue['state']})")
```
```

---

## Gap 5: No Guidance on Feature Granularity

### Current State
No guidance on whether to implement a feature **fully** or **minimally**.

### Problem
**Example: Validation**
```
Issue #8: "Add project creation"
Acceptance Criteria:
- Accept name and description
- Return project object

Validation options:
1. Minimal: Check name is not empty
2. Moderate: Check name length, description length
3. Complete: Check name uniqueness, special characters, XSS, etc.

Which level is in scope?
Current prompt: No guidance
```

### Needed Guidance
```
IMPLEMENTATION GRANULARITY RULES:

1. Acceptance Criteria Explicit?
   - "Must validate name length < 100 chars" → Implement exactly that
   - "Must accept valid name" → Implement minimal validation (not empty)

2. Error Handling?
   - If acceptance criteria mention error cases → Implement them
   - If not mentioned → Implement basic error handling only

3. Edge Cases?
   - If acceptance criteria mention edge cases → Implement them
   - If not mentioned → Implement happy path only

4. Validation?
   - Implement ONLY validations mentioned in acceptance criteria
   - Do not add "nice to have" validations

**Principle:** Implement what's required, not what's ideal
**Rationale:** Other issues may define additional validations
```

---

## Gap 6: No Related Issue Discovery

### Current State
No instruction to check if similar/related issues exist.

### Problem
Agent may duplicate work or implement something planned elsewhere.

### Example
```
Issue #12: "Add task filtering by status"

Related issues (that agent doesn't check):
- Issue #15: "Add task sorting" (might share filtering code)
- Issue #18: "Add task search" (might use same query logic)

Agent implements task filtering in isolation, then:
- Issue #15 duplicates filtering logic for sorting
- Issue #18 duplicates again for search
- Code duplication across 3 issues
```

### Missing Instructions
```
Phase 1: CONTEXT GATHERING

Step 3.5 - Related Issue Check:

AFTER reading current issue, check for related issues:

```python
# Search for related issues
current_issue_title = "Add task filtering by status"
keywords = ["task", "filter", "query", "search"]

# Check ORCH_PLAN.json for related issues
all_issues = plan_data.get('issues', [])
related_issues = [
    i for i in all_issues
    if any(kw in i['title'].lower() for kw in keywords)
    and i['issue_id'] != current_issue_iid
]

if related_issues:
    print(f"[INFO] Found {len(related_issues)} related issues:")
    for issue in related_issues:
        print(f"  - Issue #{issue['issue_id']}: {issue['title']}")
    print("[INFO] Consider code reuse opportunities")
    print("[INFO] Avoid duplicating functionality")
```

**Decision Making:**
- If related issue is COMPLETED → Reuse its code/patterns
- If related issue is PLANNED → Keep implementation minimal, note for future refactoring
- If no related issues → Implement independently
```

---

## Enhancement Recommendations

### Priority 1: Add Scope Boundary Phase (CRITICAL)

Insert **Phase 1.5: SCOPE BOUNDARY ANALYSIS** between context gathering and implementation design:

```markdown
PHASE 1.5: SCOPE BOUNDARY ANALYSIS (CRITICAL)

🚨 DEFINE EXACT SCOPE before any implementation

SCOPE DEFINITION WORKFLOW:

1. Extract Acceptance Criteria as Scope Boundary:
```python
issue = get_issue(project_id, issue_iid)
description = issue['description']

# Extract acceptance criteria
criteria_section = extract_section(description, ["Acceptance Criteria", "Akzeptanzkriterien"])
criteria = parse_criteria_list(criteria_section)

print(f"[SCOPE] This issue has {len(criteria)} acceptance criteria")
print(f"[SCOPE] Implementation MUST satisfy ALL criteria")
print(f"[SCOPE] Implementation MUST NOT add features beyond criteria")

for idx, criterion in enumerate(criteria, 1):
    print(f"  {idx}. {criterion}")
```

2. Check Issue Dependencies (from ORCH_PLAN.json):
```python
orch_plan = json.loads(get_file_contents("docs/ORCH_PLAN.json", ref="master"))

# Find current issue in plan
current_issue_plan = next(
    (i for i in orch_plan.get('issues', []) if i.get('issue_id') == issue_iid),
    None
)

if current_issue_plan and current_issue_plan.get('dependencies'):
    print(f"[DEPENDENCIES] Issue #{issue_iid} depends on: {current_issue_plan['dependencies']}")

    # Verify dependencies are completed
    for dep_id in current_issue_plan['dependencies']:
        dep_issue = get_issue(project_id, dep_id)
        if dep_issue['state'] != 'closed':
            ESCALATE(
                f"Cannot implement Issue #{issue_iid}: "
                f"depends on Issue #{dep_id} (status: {dep_issue['state']}). "
                f"Wait for dependency to be completed first."
            )

    print(f"[DEPENDENCIES] ✅ All dependency issues are completed")
else:
    print(f"[DEPENDENCIES] No dependencies - can proceed")
```

3. Identify Out-of-Scope Elements:
```python
# Common out-of-scope indicators
out_of_scope_indicators = [
    "also implement",  # "Also implement deletion" → separate issue
    "in addition",      # "In addition, add sorting" → separate issue
    "would be nice",    # "Would be nice to have X" → not required
    "future",           # "Future enhancements" → not now
    "optional"          # "Optional feature X" → not required
]

for indicator in out_of_scope_indicators:
    if indicator in description.lower():
        print(f"[WARNING] Issue description contains '{indicator}' - verify scope carefully")
```

4. Define Scope Boundaries:
```
[SCOPE BOUNDARIES DEFINED]

IN SCOPE (from acceptance criteria):
- Create project with name and description
- Validate name is not empty
- Return project with generated ID

OUT OF SCOPE (not in acceptance criteria):
❌ Project editing (different issue)
❌ Project deletion (different issue)
❌ Project listing (different issue)
❌ Project permissions (different issue)
❌ Audit logging (not mentioned)
❌ Email notifications (not mentioned)

MINIMAL HELPERS ALLOWED:
✅ validateProjectName() - needed for criterion #2
✅ generateProjectId() - needed for criterion #3
❌ ProjectValidator class - over-engineering for this issue
```

CRITICAL RULE:
**If it's not in acceptance criteria and not a minimal helper (< 10 lines), it's OUT OF SCOPE**
```

---

### Priority 2: Enhance Phase 2 with Scope Filtering (HIGH)

Modify **Phase 2: IMPLEMENTATION DESIGN** to actively filter components:

```markdown
PHASE 2: IMPLEMENTATION DESIGN

Design Principles:
1. **Follow Architecture:** Use ORCH_PLAN.json architecture decisions
2. **Match Existing Patterns:** Analyze existing code style and structure
3. **Satisfy Acceptance Criteria ONLY:** Every component must map to a criterion
4. **Minimal Implementation:** Implement exactly what's required, nothing more
5. **Test-Driven:** Consider how to test each component
6. **Dependencies:** Add to requirements.txt/pom.xml/package.json

SCOPE-FILTERED DESIGN PROCESS:

Step 1: Map Acceptance Criteria to Components
For each acceptance criterion, identify required components:

Example:
Criterion 1: "User can create project with name and description"
→ Components: createProject() method, Project class

Criterion 2: "Project name must be unique"
→ Components: checkNameUniqueness() method

Criterion 3: "Return project with generated ID"
→ Components: generateId() method

Step 2: Review Planned Components
For each planned component, verify:
- Which criterion does it satisfy?
- Is it absolutely necessary?
- Could it be in another issue?

Example:
✅ createProject() → Satisfies criterion #1
✅ checkNameUniqueness() → Satisfies criterion #2
✅ generateId() → Satisfies criterion #3
✅ Project class → Infrastructure for all criteria
❌ updateProject() → NOT in any criterion → SKIP
❌ deleteProject() → NOT in any criterion → SKIP
❌ ProjectValidator class → Over-engineering → SKIP (use simple functions)
❌ ProjectRepository class → Might be in another issue → Check ORCH_PLAN

Step 3: Check ORCH_PLAN for Deferred Components
If you need a component that seems complex/reusable:
- Check if it's planned in another issue
- If yes: Use minimal stub/placeholder
- If no: Implement minimally for this issue only

Example:
Need: UserService (to get user info)
Check ORCH_PLAN: Issue #8 implements UserService
Status: Issue #8 is completed ✅
Action: Use existing UserService

OR:

Need: EmailService (to send notifications)
Check ORCH_PLAN: Issue #15 will implement EmailService
Status: Issue #15 is not started ❌
Action: Skip email feature OR escalate if required
```

---

### Priority 3: Add Completion Scope Verification (MEDIUM)

Add to **Phase 7: AGENT REPORT** a scope adherence verification:

```markdown
## 🎯 Scope Adherence Verification

BEFORE creating report, verify scope boundaries were respected:

**Acceptance Criteria Coverage:**
- [ ] ALL acceptance criteria implemented
- [ ] NO criteria left uncovered
- [ ] NO additional features implemented beyond criteria

**Out-of-Scope Check:**
- [ ] No features implemented that weren't in acceptance criteria
- [ ] No "nice to have" features added
- [ ] No functionality from other issues implemented
- [ ] Helper functions are minimal (< 10 lines) or required

**Dependency Check:**
- [ ] All dependency issues were completed before implementation
- [ ] No dependency functionality implemented in this issue

IF any check fails → Review implementation and remove out-of-scope code
```

---

## Implementation Plan

### Week 1: Core Scope Detection
1. Add Phase 1.5: Scope Boundary Analysis
2. Add dependency checking from ORCH_PLAN.json
3. Add acceptance criteria extraction and mapping

### Week 2: Design Filtering
1. Enhance Phase 2 with scope filtering
2. Add component-to-criterion mapping
3. Add out-of-scope detection

### Week 3: Verification
1. Add scope adherence verification to Phase 7
2. Test with real issues
3. Refine based on feedback

---

## Expected Outcomes

### Before Enhancements:
- ❌ Agent may implement features from other issues
- ❌ Agent may add "helpful" features not required
- ❌ Agent may start issues before dependencies are ready
- ❌ Agent may create unnecessary helper classes
- ❌ Scope defined vaguely ("implement this issue")

### After Enhancements:
- ✅ Agent checks dependencies before starting
- ✅ Agent maps every component to acceptance criterion
- ✅ Agent skips out-of-scope features
- ✅ Agent implements minimally and precisely
- ✅ Scope defined explicitly (exact list of criteria)
- ✅ Clear boundary between in-scope and out-of-scope

---

## Success Metrics

1. **Scope Adherence Rate:** % of implementations that only include required features
   - Target: > 95%

2. **Dependency Detection:** % of times agent correctly identifies missing dependencies
   - Target: 100%

3. **Acceptance Criteria Coverage:** % of criteria covered
   - Target: 100%

4. **Out-of-Scope Prevention:** % of times agent avoids implementing extra features
   - Target: > 90%

5. **Code Reuse:** % of times agent reuses code from completed dependency issues
   - Target: > 80%

---

## Questions for Discussion

1. **Scope strictness:** Should agent NEVER add features beyond acceptance criteria, or allow minimal helpers?

2. **Dependency handling:** What if dependency issue is incomplete but agent could implement missing piece?

3. **Granularity:** Should all validation/error handling be explicit in acceptance criteria?

4. **Related issues:** Should agent proactively suggest refactoring when it sees duplication opportunities?

---

**END OF ANALYSIS**
