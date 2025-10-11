# Supervisor Debug Logging Guide

## Overview
Comprehensive debug outputs have been added to `src/orchestrator/supervisor.py` to trace the complete workflow and identify potential problems.

---

## 🎯 **Logging Categories**

### **[WORKFLOW]** - Main Flow Steps
Traces the primary execution path through the orchestration system.

### **[DEBUG]** - Detailed State Information
Provides detailed information about variables, parameters, and internal state.

### **[PRIORITY]** - Issue Priority Order
Shows the calculated priority order of issues to be implemented.

### **[OK]** / **[X]** / **[!]** - Status Indicators
- `[OK]` = Success
- `[X]` = Failure
- `[!]` = Warning (non-critical)

---

## 📋 **Complete Workflow Trace**

### **PHASE 1: Planning Agent Execution**

```
[WORKFLOW] ============================================================
[WORKFLOW] PHASE 1: Planning Agent Execution
[WORKFLOW] ============================================================
[WORKFLOW] Step 1: Planning Agent Execution
[DEBUG] Execution mode: implement
[DEBUG] Specific issue: None

[WORKFLOW] ✅ Planning Agent execution successful
[DEBUG] Planning result length: 12345 chars
```

**Purpose:** Trace Planning Agent invocation and result storage.

---

### **PHASE 1.5: Planning Branch Merge**

```
[WORKFLOW] ============================================================
[WORKFLOW] PHASE 1.5: Review Planning Work
[WORKFLOW] ============================================================
[WORKFLOW] Step 3: Checking for planning-structure branch
[DEBUG] Available branches: ['master', 'planning-structure', ...]

[WORKFLOW] ✅ Found planning-structure branch: planning-structure
[WORKFLOW] Step 4: Review Agent merging planning branch to master
[DEBUG] Review Agent result: True

[WORKFLOW] Step 5: Loading ORCH_PLAN.json from master
[WORKFLOW] ✅ Loaded ORCH_PLAN.json successfully
[DEBUG] Implementation order: ['5', '3', '7', '2', '9']
```

**Purpose:** Trace planning branch detection, merge, and ORCH_PLAN.json loading.

---

### **PHASE 2: Issue Preparation**

```
[WORKFLOW] ============================================================
[WORKFLOW] PHASE 2: Preparation
[WORKFLOW] ============================================================
[WORKFLOW] Step 6: Fetching all open issues from GitLab
[WORKFLOW] ✅ Fetched 8 open issues from GitLab
[DEBUG] Raw issue IIDs: ['1', '2', '3', '5', '7', '9', '4', '8']

[WORKFLOW] Step 7: Applying ORCH_PLAN.json priority order
[WORKFLOW] ✅ Applied planning prioritization
[DEBUG] Prioritized count: 8 issues

[WORKFLOW] Step 8: Filtering out completed issues
[WORKFLOW] ✅ After filtering: 8 issues remain
[DEBUG] Skipped 0 already-completed issues

[PRIORITY] Implementation order:
[PRIORITY]   1. Issue #5: User Authentication
[PRIORITY]   2. Issue #3: Project CRUD API
[PRIORITY]   3. Issue #7: Task Management
[PRIORITY]   4. Issue #2: Database Schema
[PRIORITY]   5. Issue #9: Frontend Components
[PRIORITY]   6. Issue #1: Project Setup
[PRIORITY]   7. Issue #4: API Documentation
[PRIORITY]   8. Issue #8: Deployment Pipeline
```

**Purpose:** Trace issue fetching, prioritization, and filtering.

---

### **PHASE 3: Implementation Loop**

```
[WORKFLOW] ============================================================
[WORKFLOW] PHASE 3: Implementation
[WORKFLOW] ============================================================
[WORKFLOW] [1/8] Processing Issue #5: User Authentication
```

**Purpose:** Show which issue is being processed in the queue.

---

### **Step 9.1: Completion Check**

```
[WORKFLOW] Step 9.1: Checking if issue #5 is already completed
[DEBUG] Issue title: User Authentication
[DEBUG] Completion check result: False
```

**Purpose:** Verify if issue needs implementation or can be skipped.

**Skipped Issue Example:**
```
[WORKFLOW] Step 9.1: Checking if issue #5 is already completed
[DEBUG] Issue title: User Authentication
[DEBUG] Completion check result: True
[WORKFLOW] [OK] Issue #5 already closed/merged - skipping
```

---

### **Step 9.2: Retry Loop Initialization**

```
[WORKFLOW] Step 9.2: Starting retry loop (max 3 attempts)

======================================================================
[WORKFLOW] Issue #5: User Authentication
[WORKFLOW] Attempt 1/3
======================================================================
```

**Purpose:** Track retry attempts for failed implementations.

**Retry Example:**
```
[WORKFLOW] [RETRY] Issue #5 - Attempt 2/3
[DEBUG] Retry delay: 10s
```

---

### **Step 9.3: Feature Branch Creation**

```
[WORKFLOW] Step 9.3: Created feature branch: feature/issue-5-user-authentication
```

**Purpose:** Show which branch will be used for this issue.

---

### **Step 10: PHASE 1/3 - Coding Agent**

```
[WORKFLOW] Step 10: PHASE 1/3 - Coding Agent Execution
[DEBUG] Target branch: feature/issue-5-user-authentication
[DEBUG] Issue IID: 5

[DEBUG] Coding Agent result: True
[WORKFLOW] [OK] Coding phase completed successfully
```

**Purpose:** Trace Coding Agent invocation and result.

**Failure Example:**
```
[DEBUG] Coding Agent result: False
[WORKFLOW] [X] Coding phase failed - will retry
```

---

### **Step 11: PHASE 2/3 - Testing Agent**

```
[WORKFLOW] Step 11: PHASE 2/3 - Testing Agent Execution
[DEBUG] Target branch: feature/issue-5-user-authentication
[DEBUG] Minimum coverage requirement: 80%

[DEBUG] Testing Agent result: True
[WORKFLOW] [OK] Testing phase completed successfully
```

**Purpose:** Trace Testing Agent invocation and result.

**Failure Example:**
```
[DEBUG] Testing Agent result: False
[WORKFLOW] [!] Testing phase failed - continuing to review
```

---

### **Step 12: PHASE 3/3 - Review Agent**

```
[WORKFLOW] Step 12: PHASE 3/3 - Review Agent Execution
[DEBUG] Target branch: feature/issue-5-user-authentication
[DEBUG] Will validate pipeline and create MR

[DEBUG] Review Agent result: True
[WORKFLOW] [OK] Review phase completed - MR merged successfully
```

**Purpose:** Trace Review Agent invocation and MR creation.

**Failure Example:**
```
[DEBUG] Review Agent result: False
[WORKFLOW] [X] Review phase failed - will retry
```

---

### **Step 13: Mark Issue Complete**

```
[WORKFLOW] Step 13: Marking issue #5 as complete
```

**Purpose:** Track issue completion state update.

---

### **Step 14: Export Analytics**

```
[WORKFLOW] Step 14: Exporting analytics to CSV
[DEBUG] Issue report exported successfully

[WORKFLOW] [OK] Issue #5 COMPLETED SUCCESSFULLY
```

**Purpose:** Trace analytics export to CSV.

---

### **Error Handling & Retry**

```
[WORKFLOW] [X] Exception occurred during implementation
[DEBUG] Error type: GitLabAPIError
[DEBUG] Error message: 401 Unauthorized

[DEBUG] Recording error in issue tracker
[WORKFLOW] Will retry (attempt 1/3)
```

**Purpose:** Trace exceptions and retry logic.

**Final Failure Example:**
```
[WORKFLOW] [X] All retries exhausted - marking as failed

[WORKFLOW] [X] Issue #5 FAILED after 3 attempts
[WORKFLOW] Finalizing failed issue and exporting to CSV
[DEBUG] Failed issue report exported
```

---

## 🔍 **How to Use This Logging**

### **1. Trace Issue Order Problems**
Look for `[PRIORITY]` logs to see calculated implementation order:
```bash
grep "\[PRIORITY\]" logs/orchestrator_run.log
```

### **2. Debug Completion Check Issues**
Look for `Step 9.1` to see why issues are skipped or processed:
```bash
grep "Step 9.1" logs/orchestrator_run.log
```

### **3. Trace Agent Failures**
Look for `[X]` markers to find failing agents:
```bash
grep "\[X\]" logs/orchestrator_run.log
```

### **4. Monitor Retry Attempts**
Look for `[RETRY]` to see which issues needed retries:
```bash
grep "\[RETRY\]" logs/orchestrator_run.log
```

### **5. Verify Planning Branch Merge**
Look for `PHASE 1.5` to see planning branch handling:
```bash
grep "PHASE 1.5" -A 20 logs/orchestrator_run.log
```

---

## 📊 **Debug Output Flow Diagram**

```
[WORKFLOW] PHASE 1: Planning
    └─> Step 1: Planning Agent Execution
    └─> ✅ Planning successful

[WORKFLOW] PHASE 1.5: Review Planning
    └─> Step 3: Check for planning-structure branch
    └─> Step 4: Merge planning branch to master
    └─> Step 5: Load ORCH_PLAN.json
    └─> ✅ Implementation order loaded

[WORKFLOW] PHASE 2: Preparation
    └─> Step 6: Fetch all open issues
    └─> Step 7: Apply ORCH_PLAN.json priority
    └─> Step 8: Filter completed issues
    └─> [PRIORITY] Show implementation order

[WORKFLOW] PHASE 3: Implementation
    └─> For Each Issue:
        └─> Step 9.1: Check if already completed
        └─> Step 9.2: Start retry loop
        └─> Step 9.3: Create feature branch
        └─> Step 10: Coding Agent (PHASE 1/3)
        └─> Step 11: Testing Agent (PHASE 2/3)
        └─> Step 12: Review Agent (PHASE 3/3)
        └─> Step 13: Mark issue complete
        └─> Step 14: Export analytics to CSV
        └─> ✅ Issue completed OR ❌ Issue failed
```

---

## 🚨 **Common Debug Scenarios**

### **Scenario 1: Issue Implemented in Wrong Order**
**Look For:**
```
[PRIORITY] Implementation order:
[PRIORITY]   1. Issue #3: ...
[PRIORITY]   2. Issue #5: ...  # Wrong! Should be first
```
**Diagnosis:** ORCH_PLAN.json has incorrect priority order.

---

### **Scenario 2: Issue Skipped Incorrectly**
**Look For:**
```
[WORKFLOW] Step 9.1: Checking if issue #5 is already completed
[DEBUG] Completion check result: True  # But issue is NOT complete!
[WORKFLOW] [OK] Issue #5 already closed/merged - skipping
```
**Diagnosis:** `is_issue_completed()` logic has false positive.

---

### **Scenario 3: Infinite Retry Loop**
**Look For:**
```
[WORKFLOW] [RETRY] Issue #5 - Attempt 2/3
[DEBUG] Coding Agent result: False
[WORKFLOW] [X] Coding phase failed - will retry

[WORKFLOW] [RETRY] Issue #5 - Attempt 3/3
[DEBUG] Coding Agent result: False
[WORKFLOW] [X] Coding phase failed - will retry

[WORKFLOW] [X] All retries exhausted - marking as failed
```
**Diagnosis:** Agent is not fixing the root cause between retries.

---

### **Scenario 4: Planning Branch Not Found**
**Look For:**
```
[WORKFLOW] Step 3: Checking for planning-structure branch
[DEBUG] Available branches: ['master', 'feature/...']
[WORKFLOW] ⚠️ No planning-structure branch found - skipping merge
```
**Diagnosis:** Planning Agent did not create branch (fresh repo).

---

### **Scenario 5: ORCH_PLAN.json Missing**
**Look For:**
```
[WORKFLOW] Step 5: Loading ORCH_PLAN.json from master
[WORKFLOW] ⚠️ ORCH_PLAN.json not found - will use fallback prioritization
```
**Diagnosis:** Planning Agent did not create ORCH_PLAN.json or it wasn't merged.

---

## ✅ **Verification Checklist**

After adding debug outputs, verify:

- [ ] All phases (1, 1.5, 2, 3) have clear `[WORKFLOW]` markers
- [ ] Each agent execution (Coding, Testing, Review) has `[DEBUG]` result logging
- [ ] Retry logic shows attempt numbers and delays
- [ ] Completion check shows exact reason for skip/process decision
- [ ] Error handling shows exception type and message
- [ ] Success/failure states are clearly marked with `✅` or `❌`
- [ ] Analytics export is confirmed with `[DEBUG]` messages

---

## 🎯 **Key Takeaways**

1. **Complete Traceability**: Every major workflow step is logged with numbered steps
2. **Debug Detail**: All critical variables (branch, IID, results) are logged
3. **Status Clarity**: Clear success/failure/warning indicators throughout
4. **Retry Tracking**: Full visibility into retry attempts and reasons
5. **Problem Detection**: Logs designed to quickly identify common issues
6. **CSV Export**: All analytics are logged and exportable for analysis

This logging system enables full end-to-end tracing of the orchestration workflow, making it easy to identify and debug any problems that arise during execution.
