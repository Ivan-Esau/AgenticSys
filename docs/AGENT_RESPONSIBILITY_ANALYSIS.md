# Agent Responsibility Analysis

## Executive Summary

Analysis of Coding Agent and Testing Agent prompts reveals **3 critical issues** and **5 areas for improvement** regarding separation of concerns and report-based workflow.

---

## ✅ What's Working Correctly

### Coding Agent (Good)
- **Scope**: Correctly restricted to source code only (lines 454-460)
- **Prohibitions**: Explicitly forbidden from creating test files (line 471)
- **Report Reading**: Reads existing reports in Phase 0 (lines 116-166)
- **Pipeline Focus**: Monitors pipeline for compilation verification (lines 302-333)

### Testing Agent (Good)
- **Scope**: Correctly restricted to test code only (lines 454-462)
- **Prohibitions**: Explicitly forbidden from modifying production code (line 474)
- **Report Reading**: Reads existing reports in Phase 0 (lines 124-176)
- **Pipeline Focus**: Monitors pipeline for test job verification (lines 292-333)

---

## 🚨 Critical Issues Found

### Issue 1: Coding Agent Pipeline Verification Ambiguity

**Location**: `coding_prompts.py`, Phase 4 (lines 302-333)

**Problem**: Coding Agent currently says:
```python
status = get_pipeline(pipeline_id=YOUR_PIPELINE_ID)['status']

if status == "success":
    proceed_to_report()
elif status in ["pending", "running"]:
    wait()  # Continue monitoring
elif status == "failed":
    analyze_and_fix()  # Go to Phase 5
```

**Issue**: This checks OVERALL pipeline status, not specifically BUILD/COMPILE job status. If test job fails but build succeeds, Coding Agent might incorrectly go to "analyze_and_fix" mode.

**Fix Required**:
```python
# Get pipeline status
pipeline = get_pipeline(pipeline_id=YOUR_PIPELINE_ID)

# Get specific job statuses
jobs = get_pipeline_jobs(pipeline_id=YOUR_PIPELINE_ID)
build_jobs = [j for j in jobs if 'build' in j['name'].lower() or 'compile' in j['name'].lower()]
test_jobs = [j for j in jobs if 'test' in j['name'].lower()]

# Coding Agent ONLY cares about BUILD job
if all(j['status'] == 'success' for j in build_jobs):
    print("[CODING] ✅ Build/compile job passed - my work is done")
    proceed_to_report()
elif test_jobs and any(j['status'] == 'failed' for j in test_jobs):
    print("[CODING] ⚠️ Test job failed - NOT MY RESPONSIBILITY")
    print("[CODING] ✅ Build succeeded - proceeding to completion")
    proceed_to_report()
elif any(j['status'] == 'failed' for j in build_jobs):
    print("[CODING] ❌ Build job failed - analyzing and fixing")
    analyze_and_fix()
```

---

### Issue 2: Testing Agent Should Never Diagnose Implementation Bugs

**Location**: `testing_prompts.py`, Phase 0 (lines 158-164)

**Current Text**:
```
**RETRY_TESTS_FAILED:** (Test debugging)
1. Read latest testing report for failure details
2. Read EXISTING test files (don't recreate!)
3. Analyze: Are tests CORRECT (implementation bug) or INCORRECT (test bug)?
4. If tests are correct: Report implementation issues, skip to PHASE 5
5. If tests are incorrect: Fix test assertions/logic
```

**Problem**: Step 4 says "Report implementation issues" - Testing Agent should NEVER decide there's an implementation bug. This is outside its scope.

**Fix Required**:
```
**RETRY_TESTS_FAILED:** (Test debugging)
1. Read latest testing report for failure details
2. Read EXISTING test files (don't recreate!)
3. Analyze: Are tests INCORRECT (bad assertions, wrong logic)?
4. If tests have bugs: Fix test assertions/logic, commit, verify
5. If tests are correct but still fail:
   - TEST FAILURES ARE ALWAYS TEST BUGS until proven otherwise
   - Try simpler assertions, more robust mocking, better setup
   - Max 3 attempts to make tests pass
   - After 3 attempts: ESCALATE to supervisor with analysis

🚨 NEVER assume implementation is wrong - that's supervisor's decision
🚨 NEVER report "implementation bugs" - only report persistent test failures
```

---

### Issue 3: Pipeline Job Specificity Missing

**Location**: Both agents

**Problem**: Neither agent explicitly documents which pipeline JOB they care about:
- Coding Agent should only care about: `build`, `compile`, `lint` jobs
- Testing Agent should only care about: `test`, `pytest`, `junit`, `jest` jobs

**Fix Required**: Add explicit job filtering section to both agents:

**For Coding Agent**:
```python
CRITICAL: CODING AGENT JOB SCOPE

🚨 YOU ONLY CARE ABOUT THESE JOBS:
✅ build (compilation)
✅ compile (type checking, syntax validation)
✅ lint (code style, optional)

❌ YOU DO NOT CARE ABOUT THESE JOBS:
❌ test / pytest / junit / jest (Testing Agent's responsibility)
❌ coverage (Testing Agent's responsibility)
❌ deploy (Review Agent's responsibility)

VERIFICATION LOGIC:
```python
jobs = get_pipeline_jobs(pipeline_id=YOUR_PIPELINE_ID)

# Filter for YOUR jobs only
my_jobs = [j for j in jobs if any(keyword in j['name'].lower()
           for keyword in ['build', 'compile', 'lint'])]

# Check if YOUR jobs passed
if all(j['status'] == 'success' for j in my_jobs):
    print("[CODING] ✅ All my jobs passed (build/compile/lint)")
    proceed_to_completion()
else:
    print("[CODING] ❌ My jobs failed - debugging")
    debug_and_fix()
```

**For Testing Agent**:
```python
CRITICAL: TESTING AGENT JOB SCOPE

🚨 YOU ONLY CARE ABOUT THESE JOBS:
✅ test / pytest / junit / jest (test execution)
✅ coverage (test coverage validation, optional)

❌ YOU DO NOT CARE ABOUT THESE JOBS:
❌ build / compile (Coding Agent's responsibility)
❌ lint (Coding Agent's responsibility)
❌ deploy (Review Agent's responsibility)

VERIFICATION LOGIC:
```python
jobs = get_pipeline_jobs(pipeline_id=YOUR_PIPELINE_ID)

# Filter for YOUR jobs only
my_jobs = [j for j in jobs if any(keyword in j['name'].lower()
           for keyword in ['test', 'pytest', 'junit', 'jest', 'coverage'])]

# Check if YOUR jobs passed
if all(j['status'] == 'success' for j in my_jobs):
    print("[TESTING] ✅ All my jobs passed (test/coverage)")
    proceed_to_completion()
else:
    print("[TESTING] ❌ My jobs failed - debugging tests")
    debug_and_fix_tests()
```

---

## 📋 Areas for Improvement

### 1. Explicit Job Naming Convention

**Add to both agents**:
```markdown
PIPELINE JOB NAMING CONVENTIONS:

Standard job names in .gitlab-ci.yml:
- `build` - Compiles source code (Coding Agent scope)
- `test` - Runs test suite (Testing Agent scope)
- `lint` - Code style checks (Coding Agent scope, optional)
- `coverage` - Test coverage check (Testing Agent scope, optional)

🚨 CRITICAL: Always filter jobs by name to determine responsibility
🚨 CRITICAL: Never assume overall pipeline status means YOUR jobs passed
```

### 2. Report Reading Specificity

**Current**: Both agents read reports but don't specify WHAT to extract

**Add to Coding Agent**:
```markdown
REPORT READING FOR CODING AGENT:

When reading ReviewAgent or TestingAgent reports:

✅ LOOK FOR:
- "Build failed" / "Compilation error"
- "Syntax error in src/..."
- "Import error in src/..."
- "Type error in src/..."
- "Missing dependency in requirements.txt/pom.xml"
- Line numbers and file names in src/ directory

❌ IGNORE:
- "Test failed" / "Assertion error"
- "Test failure in tests/..."
- Coverage percentages
- Test execution details
```

**Add to Testing Agent**:
```markdown
REPORT READING FOR TESTING AGENT:

When reading CodingAgent or previous TestingAgent reports:

✅ LOOK FOR:
- "Test failed: test_name"
- "Assertion error: expected X, got Y"
- "Test failure in tests/..."
- "No tests found" / "0 tests executed"
- "ModuleNotFoundError in test file"
- Coverage below threshold

❌ IGNORE:
- "Build failed" / "Compilation error"
- "Syntax error in src/..."
- Implementation bugs or code issues
- Architectural decisions
```

### 3. Clear Completion Criteria

**Add to Coding Agent** (line 547):
```markdown
COMPLETION SIGNAL REQUIREMENTS:

✅ Signal CODING_PHASE_COMPLETE when:
1. Build/compile job status === "success"
2. Lint job status === "success" (if exists)
3. Source code files created/modified successfully
4. Dependencies updated (requirements.txt, pom.xml, package.json)
5. Agent report created

❌ DO NOT WAIT FOR:
- Test job to complete
- Test job to pass
- Coverage validation
- Review approval

🚨 YOUR JOB IS DONE when BUILD succeeds, even if TESTS haven't run yet
```

**Add to Testing Agent** (line 532):
```markdown
COMPLETION SIGNAL REQUIREMENTS:

✅ Signal TESTING_PHASE_COMPLETE when:
1. Test job status === "success"
2. Coverage job status === "success" (if exists)
3. ALL acceptance criteria have tests
4. ALL tests PASS (0 failures)
5. Tests actually executed (verified in trace)
6. Agent report created

❌ DO NOT WAIT FOR:
- Build job (already done by Coding Agent)
- Lint job (already done by Coding Agent)
- Review approval
- Merge to master

🚨 YOUR JOB IS DONE when ALL TESTS PASS, regardless of build status
```

### 4. Error Escalation Matrix

**Add to both agents**:
```markdown
WHEN TO ESCALATE TO SUPERVISOR:

CODING AGENT ESCALATIONS:
✅ Build fails after 3 fix attempts
✅ Missing dependency can't be resolved
✅ Architecture decisions unclear from ORCH_PLAN.json
✅ Issue requirements conflict with existing code
✅ Pipeline pending > 20 minutes

❌ DON'T ESCALATE FOR:
- Test failures (Testing Agent's problem)
- Coverage issues (Testing Agent's problem)

TESTING AGENT ESCALATIONS:
✅ Tests fail after 3 fix attempts
✅ Can't determine how to test a requirement
✅ Implementation doesn't match acceptance criteria
✅ No implementation files found for testing
✅ Pipeline pending > 20 minutes

❌ DON'T ESCALATE FOR:
- Build failures (Coding Agent's problem)
- Compilation errors (Coding Agent's problem)
- Missing dependencies (Coding Agent's problem)
```

### 5. Agent Communication Protocol

**Add section to both agents**:
```markdown
AGENT-TO-AGENT COMMUNICATION (via Reports)

CODING AGENT → TESTING AGENT:
In your report, include:
```markdown
## 💡 Notes for Testing Agent
- Test these specific functions: [list]
- Pay attention to edge cases: [specific cases]
- Mock these dependencies: [list]
- Expected behavior: [description]
- Known limitations: [list]
```

TESTING AGENT → REVIEW AGENT:
In your report, include:
```markdown
## 💡 Notes for Review Agent
- All acceptance criteria tested: [list with test names]
- Coverage: [percentage and details]
- Test strategy: [unit/integration/e2e]
- Known flaky tests: [none or list]
```

REVIEW AGENT → CODING/TESTING AGENT:
In rejection report, be specific:
```markdown
## 🔧 Required Fixes for Coding Agent
- Fix implementation bug in src/api/auth.py:45
- Add validation for empty username

## 🔧 Required Fixes for Testing Agent
- Add test for empty username case
- Fix assertion in test_login_invalid_credentials
```

🚨 ALWAYS read the "Notes for [Your Agent]" section first
🚨 ALWAYS specify which agent needs to fix what in rejection reports
```

---

## 🎯 Recommended Changes Summary

### Priority 1 (Critical - Must Fix):
1. **Coding Agent Phase 4**: Add job-specific filtering (build/compile only)
2. **Testing Agent Phase 0**: Remove "Report implementation issues" logic
3. **Both Agents**: Add explicit job scope sections

### Priority 2 (Important - Should Fix):
4. **Both Agents**: Add report reading specificity sections
5. **Both Agents**: Add clear completion criteria sections

### Priority 3 (Good to Have):
6. **Both Agents**: Add error escalation matrix
7. **Both Agents**: Add agent communication protocol

---

## 📝 Implementation Checklist

- [ ] Update Coding Agent Phase 4 with job filtering
- [ ] Update Testing Agent Phase 0 to remove implementation diagnosis
- [ ] Add "JOB SCOPE" section to Coding Agent constraints
- [ ] Add "JOB SCOPE" section to Testing Agent constraints
- [ ] Add "REPORT READING" section to both agents
- [ ] Update completion criteria in both agents
- [ ] Add escalation matrix to both agents
- [ ] Add agent communication protocol to both agents
- [ ] Test changes with sample workflow
- [ ] Verify agents don't overstep boundaries

---

## 📊 Expected Outcomes

After implementing these changes:

1. **Coding Agent** will:
   - ✅ Complete when build succeeds, even if tests haven't started
   - ✅ Never debug test failures
   - ✅ Read reports focusing only on compilation issues
   - ✅ Clearly communicate implementation details to Testing Agent

2. **Testing Agent** will:
   - ✅ Complete when all tests pass, regardless of build status
   - ✅ Never modify production code
   - ✅ Never diagnose implementation bugs
   - ✅ Only fix test code or escalate after 3 attempts

3. **Overall System** will:
   - ✅ Have clear handoff points between agents
   - ✅ Reduce circular dependencies and confusion
   - ✅ Improve success rate through focused responsibilities
   - ✅ Enable faster debugging through clear escalation paths
