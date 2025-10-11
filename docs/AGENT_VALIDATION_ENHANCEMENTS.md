# Agent Validation Enhancements

## ✅ **Summary of Changes**

Enhanced agent prompts to **emphasize** that all agents must fetch the actual GitLab issue and validate against ALL requirements and acceptance criteria.

---

## 🎯 **What Was Already Correct**

**All agents already had the right instructions:**
- ✅ Coding Agent: Fetches issue with `get_issue()`, extracts requirements
- ✅ Testing Agent: MANDATORY PHASE 1.5 to fetch issue and test ALL acceptance criteria
- ✅ Review Agent: MANDATORY PHASE 2.5 to validate ALL requirements and criteria before merge

**No structural changes were needed** - just added emphasis and cross-references.

---

## 📝 **Changes Made**

### **1. Coding Agent** (`coding_prompts.py`)

**Enhanced Step 3: Issue Analysis**

BEFORE:
```
Step 3 - Issue Analysis:
• Use get_issue(project_id, issue_iid) → Get requirements
```

AFTER:
```
Step 3 - Issue Analysis (MANDATORY - Fetch Full Issue):
🚨 CRITICAL: You MUST fetch the actual GitLab issue, not rely only on plan_json

• Use get_issue(project_id, issue_iid) → Get COMPLETE requirements

✅ Implement to satisfy ALL requirements and acceptance criteria
✅ Testing Agent will verify you covered ALL acceptance criteria
✅ Review Agent will check you implemented ALL requirements
```

**Enhanced Report Structure**

Added explicit requirement checklist:

```markdown
## 📋 Requirements Coverage (from GitLab Issue)
- [X] Requirement 1: {{description}} - Implemented in {{file:line}}
- [X] Requirement 2: {{description}} - Implemented in {{file:line}}
- [X] Requirement 3: {{description}} - Implemented in {{file:line}}
(List ALL requirements from issue - NONE should be unchecked)

## 📝 Acceptance Criteria Coverage (from GitLab Issue)
- [X] Criterion 1: {{description}} - Implemented in {{file:line}}
- [X] Criterion 2: {{description}} - Implemented in {{file:line}}
(List ALL acceptance criteria from issue - NONE should be unchecked)
```

---

### **2. Testing Agent** (`testing_prompts.py`)

**Enhanced PHASE 1.5: Acceptance Criteria Extraction**

BEFORE:
```
PHASE 1.5: ACCEPTANCE CRITERIA EXTRACTION (MANDATORY)

🚨 CRITICAL: Tests must validate acceptance criteria from issue, not just code coverage.
```

AFTER:
```
PHASE 1.5: ACCEPTANCE CRITERIA EXTRACTION (MANDATORY)

🚨 CRITICAL: Tests must validate acceptance criteria from GitLab issue, not just code coverage.
🚨 CRITICAL: You MUST fetch the actual GitLab issue with get_issue(), not rely on Coding Agent report.

📋 Review Agent will verify you tested ALL acceptance criteria from the issue - NONE can be skipped.
```

**Enhanced Validation Checklist:**

```
✅ Full GitLab issue fetched with get_issue()
✅ ALL criteria extracted and documented
✅ Each criterion has at least one test
✅ Test names clearly map to criteria
✅ EVERY criterion from issue has corresponding test (no exceptions)
```

---

### **3. Review Agent** (`review_prompts.py`)

**Enhanced PHASE 2.5: Comprehensive Validation**

BEFORE:
```
PHASE 2.5: COMPREHENSIVE REQUIREMENT & ACCEPTANCE CRITERIA VALIDATION (MANDATORY)

🚨 CRITICAL: Before merging, validate ALL requirements and acceptance criteria are met.

This is the FINAL CHECKPOINT before merge.
```

AFTER:
```
PHASE 2.5: COMPREHENSIVE REQUIREMENT & ACCEPTANCE CRITERIA VALIDATION (MANDATORY)

🚨 CRITICAL: This is the FINAL CHECKPOINT before merge. You are the last line of defense.
🚨 CRITICAL: You MUST fetch the actual GitLab issue and validate EVERYTHING.

📋 You must verify:
- Coding Agent implemented ALL requirements from the GitLab issue
- Testing Agent tested ALL acceptance criteria from the GitLab issue
- Nothing was skipped, forgotten, or left incomplete

DO NOT rely on agent reports alone - fetch the issue and verify against the source of truth.

This is the FINAL CHECKPOINT before merge. Review Agent must verify:
1. Technical validation (pipeline success)
2. Functional validation (ALL requirements met) ← MANDATORY here
3. Quality validation (ALL acceptance criteria tested) ← MANDATORY here
```

---

## 🔄 **Information Flow (Enhanced)**

```
┌─────────────────────────────────────────────────────────────┐
│ GitLab Issue (Source of Truth)                              │
│ - Requirements (Anforderungen / Requirements)               │
│ - Acceptance Criteria (Akzeptanzkriterien / Criteria)       │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├─────────────────┐
               │                 │
               ▼                 ▼
    ┌──────────────────┐  ┌──────────────────┐
    │ Coding Agent     │  │ Planning Agent   │
    │ get_issue()      │  │ ORCH_PLAN.json   │
    │ ALL Requirements │  │ Architecture     │
    └──────┬───────────┘  └──────────────────┘
           │
           │ Implementation
           │
           ▼
    ┌──────────────────┐
    │ Testing Agent    │
    │ get_issue()      │◄──── Fetches issue AGAIN (not from Coding Report)
    │ ALL Criteria     │
    └──────┬───────────┘
           │
           │ Tests
           │
           ▼
    ┌──────────────────┐
    │ Review Agent     │
    │ get_issue()      │◄──── Fetches issue AGAIN (final verification)
    │ Validates ALL    │
    └──────┬───────────┘
           │
           ▼
    ┌──────────────────┐
    │ Merge to Master  │
    │ (Only if ALL OK) │
    └──────────────────┘
```

---

## ✅ **What Each Agent Now Explicitly Knows**

### **Coding Agent:**
- ✅ MUST fetch actual GitLab issue
- ✅ Implement ALL requirements
- ✅ Cover ALL acceptance criteria
- ✅ Testing Agent will verify criteria coverage
- ✅ Review Agent will verify requirement implementation
- ✅ Must create explicit checklist in report

### **Testing Agent:**
- ✅ MUST fetch actual GitLab issue (not rely on Coding report)
- ✅ Test ALL acceptance criteria (EVERY one)
- ✅ Review Agent will verify no criteria were skipped
- ✅ Cannot complete without ALL criteria tested

### **Review Agent:**
- ✅ FINAL CHECKPOINT - last line of defense
- ✅ MUST fetch actual GitLab issue
- ✅ Verify Coding implemented ALL requirements
- ✅ Verify Testing tested ALL acceptance criteria
- ✅ Cannot merge if ANYTHING is missing
- ✅ Do NOT rely only on agent reports

---

## 🎯 **Key Improvements**

1. **Explicit Emphasis:**
   - Made it crystal clear agents must fetch the issue
   - Added "ALL" and "EVERY" to prevent skipping

2. **Cross-References:**
   - Each agent knows what the next agent will check
   - Creates accountability chain

3. **Explicit Checklists:**
   - Coding Agent must list ALL requirements and criteria
   - Makes it visible what was covered

4. **Final Checkpoint:**
   - Review Agent is "last line of defense"
   - Must verify EVERYTHING against GitLab issue

---

## ✅ **Verification**

All three agent prompt files compile successfully:
```bash
✓ coding_prompts.py
✓ testing_prompts.py
✓ review_prompts.py
```

---

## 📋 **What This Guarantees**

**Before merge, the system ensures:**
1. ✅ Coding Agent fetched issue and implemented ALL requirements
2. ✅ Testing Agent fetched issue and tested ALL acceptance criteria
3. ✅ Review Agent fetched issue and verified EVERYTHING
4. ✅ No requirement can be skipped
5. ✅ No acceptance criterion can be skipped
6. ✅ Pipeline must be successful
7. ✅ Only complete, fully validated work gets merged

**Result:** Fully working software that meets ALL requirements from the GitLab issues.
