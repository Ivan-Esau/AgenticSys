# Tool Error Handling Reference

**Quick Reference:** This document provides detailed error recovery strategies. Agents should reference this when encountering errors, but don't need to memorize every pattern.

## Error Categorization

### Network/Transient Errors
**Symptoms:** Connection timeout, 500/502/503, rate limit
**Recovery:** Retry with exponential backoff (1s, 2s, 4s) - max 3 attempts

### Missing Parameter Errors
**Symptoms:** "Required field X", "Invalid arguments"
**Recovery:** Identify missing param, add it, retry once

### Resource Not Found Errors
**Symptoms:** Branch/file/issue not found
**Recovery:** Check if resource needs creation → create → retry

### Permission Errors
**Symptoms:** 401/403, "Permission denied"
**Recovery:** Escalate immediately (cannot fix programmatically)

### Validation Errors
**Symptoms:** "Invalid format", "Validation failed"
**Recovery:** Fix format per error message, retry once

## Recovery Patterns

### Pattern 1: Transient Error Recovery
```python
max_retries = 3
for attempt in range(1, max_retries + 1):
    print(f"[RETRY] Attempt {attempt}/{max_retries}")
    wait_time = 2 ** (attempt - 1)  # 1s, 2s, 4s
    time.sleep(wait_time)

    try:
        result = retry_operation()
        print(f"[SUCCESS] Recovered on attempt {attempt}")
        break
    except Exception as e:
        if attempt == max_retries:
            escalate_error(e, attempts=max_retries)
```

### Pattern 2: Missing Parameter Recovery
```python
# Error: "branch: Required"
print(f"[FIX] Adding missing parameter: branch")
retry_with_params(branch=work_branch, ...)
```

### Pattern 3: Resource Creation
```python
# Error: "Branch not found"
print(f"[FIX] Creating missing branch")
create_branch(branch_name=work_branch, ref="master")
retry_original_operation()
```

### Pattern 4: Validation Fix
```python
# Error: "Invalid format: title must not be empty"
print(f"[FIX] Correcting validation issue")
fix_validation_issue()
retry_once()
```

## Escalation Criteria

Escalate when:
- Max retries exceeded (3 for transient, 1 for fixable)
- Permission/auth errors
- Unknown error patterns
- Circular dependencies
- Data inconsistencies

**Escalation Format:**
```
ESCALATION_REQUIRED:
Tool: {tool_name}
Error: {error_message}
Recovery Attempted: {actions}
Context: {relevant_params}
Recommendation: {next_steps}
```

## Error Context Tracking

Track for every error:
- Tool name
- Parameters used
- Error message
- Attempt number
- Recovery action
- Recovery outcome
- Timestamp

## Decision Tree

```
Error Occurred
├─ Retryable? (Network/500/rate limit)
│  ├─ YES → Exponential backoff (max 3)
│  │  ├─ Success → Continue
│  │  └─ Failed → Escalate with context
│  └─ NO → Check if fixable
│     ├─ Fixable? (Missing param/not found/validation)
│     │  ├─ YES → Fix and retry once
│     │  │  ├─ Success → Continue
│     │  │  └─ Failed → Escalate
│     │  └─ NO → Escalate immediately
│     └─ Permission/Unknown → Escalate immediately
```

## Agent-Specific Patterns

### Coding Agent
- **Compilation errors:** Read trace, fix specific issue, commit, monitor NEW pipeline
- **Dependency errors:** Add to requirements.txt/pom.xml/package.json
- **Branch not found:** Create branch, then retry file operations

### Testing Agent
- **Test failures:** Analyze trace, fix test code, commit, monitor NEW pipeline
- **Import errors:** Fix import paths, add __init__.py
- **Network failures:** Wait 60s, retry (max 2 network retries)

### Review Agent
- **Pipeline failures:** Get job traces, categorize (test/build/network), handle accordingly
- **Merge conflicts:** Escalate (manual resolution needed)
- **Network failures during merge:** Retry with 30s delay (max 2)

## Critical Rules

✅ **Always:**
- Log error type and recovery action
- Use exponential backoff for transient errors
- Single retry for fixable errors
- Preserve error context for debugging
- Get NEW pipeline ID after each commit

❌ **Never:**
- Retry permission errors
- Ignore error context
- Give up without attempting recovery
- Retry indefinitely
- Skip error categorization
- Reuse old pipeline IDs after fixes
