# Agent Behavior Principles

## Core Philosophy
Agents must work within their defined scope and NEVER modify system infrastructure to avoid dealing with problems. When encountering failures, agents must fix the actual issues rather than changing the testing/validation framework.

## Pipeline Management Rules

### 1. Pipeline is Sacred
- The CI/CD pipeline (`.gitlab-ci.yml`) is created and managed by the **SYSTEM ONLY**
- Agents must **NEVER** modify pipeline configuration unless explicitly fixing a configuration error
- Pipeline structure must remain consistent across all projects for research comparability

### 2. Agent Scope Boundaries

#### Planning Agent
**ALLOWED:**
- Analyze project requirements and issues
- Create project documentation (README, ORCH_PLAN.json)
- Define implementation strategy
- Prioritize issues based on dependencies

**FORBIDDEN:**
- Creating or modifying `.gitlab-ci.yml`
- Setting up CI/CD infrastructure
- Changing build configurations

#### Coding Agent
**ALLOWED:**
- Implement features according to issues
- Write production code
- Create necessary project files (source code, configs)
- Fix compilation and runtime errors

**FORBIDDEN:**
- Modifying `.gitlab-ci.yml`
- Changing test configurations to make tests pass
- Disabling failing tests

#### Testing Agent
**ALLOWED:**
- Write test cases for implemented features
- Fix test code when tests fail
- Add test dependencies to project files (pom.xml, package.json)
- Debug and fix actual test failures

**FORBIDDEN:**
- Modifying `.gitlab-ci.yml`
- Lowering coverage thresholds
- Commenting out failing tests
- Changing pipeline test commands

#### Review Agent
**ALLOWED:**
- Review code quality
- Create merge requests
- Suggest improvements
- Verify all tests pass

**FORBIDDEN:**
- Modifying `.gitlab-ci.yml`
- Bypassing failed pipelines
- Merging with failing tests

## Agent Workflow

### Correct Implementation Flow

1. **Planning Phase**
   - Planning Agent analyzes issues and creates project structure
   - Creates `planning-structure-*` branch if needed
   - Does NOT wait for pipeline or create merge requests
   - Completes with "PLANNING_PHASE_COMPLETE"

2. **Planning Review Phase** (Critical - was missing!)
   - Review Agent reviews planning-structure branch
   - WAITS for pipeline to be GREEN
   - Merges planning branch to main/master
   - Only proceeds if pipeline passes

3. **Implementation Phase**
   - For each issue:
     - Coding Agent implements on feature branch
     - Testing Agent adds tests
     - Review Agent waits for GREEN pipeline and merges

### Pipeline Responsibility Matrix

| Agent | Can Create Pipeline | Must Wait for Pipeline | Can Merge |
|-------|-------------------|----------------------|-----------|
| Planning | ❌ No | ❌ No | ❌ No |
| Coding | ❌ No | ❌ No | ❌ No |
| Testing | ❌ No | ✅ Yes (monitoring) | ❌ No |
| Review | ❌ No | ✅ Yes (before merge) | ✅ Yes |
| System | ✅ Yes | N/A | N/A |

## Failure Handling Protocol

### When Pipeline Fails (Red)
1. **ANALYZE** the failure logs to understand the root cause
2. **IDENTIFY** whether it's a code, test, or configuration issue
3. **FIX** the actual problem:
   - Code errors: Fix the implementation
   - Test failures: Fix the test or the code being tested
   - Missing dependencies: Add to pom.xml/package.json
   - Configuration issues: Fix project configs (NOT pipeline)
4. **VERIFY** the pipeline turns green after fixes
5. **NEVER** modify the pipeline to avoid the problem

### Examples of Correct Behavior

#### ✓ GOOD: Fixing Test Failures
```
Pipeline fails with: "Tests run: 5, Failures: 2"
Action: Analyze failing tests, fix the code or test logic
Result: Pipeline passes with all tests green
```

#### ✗ BAD: Avoiding Test Failures
```
Pipeline fails with: "Tests run: 5, Failures: 2"
Action: Modify .gitlab-ci.yml to skip tests
Result: Pipeline passes but problems remain
```

#### ✓ GOOD: Fixing Build Errors
```
Pipeline fails with: "Compilation failure: package does not exist"
Action: Add missing dependency to pom.xml
Result: Build succeeds, pipeline continues
```

#### ✗ BAD: Bypassing Build Errors
```
Pipeline fails with: "Compilation failure: package does not exist"
Action: Modify .gitlab-ci.yml to use different build command
Result: Pipeline configuration becomes inconsistent
```

## System-Level Pipeline Management

### Pipeline Creation
- Handled by `PipelineManager` and `PipelineConfig` classes
- Configured through Web GUI or CLI with tech stack parameters
- Generates standardized 3-stage pipelines (build, test, deploy)
- Includes coverage thresholds from configuration

### Pipeline Consistency
- All pipelines follow the same structure for comparability:
  ```yaml
  stages:
    - build
    - test
    - deploy
  ```
- Coverage tools are language-specific but output format is standardized
- Pipeline metrics are collected uniformly across all projects

### Research Requirements
- Pipelines must be comparable across different tech stacks
- Coverage thresholds must be consistently enforced
- Build/test/deploy stages must follow the same pattern
- Metrics collection must be uniform

## Enforcement Mechanisms

### 1. Prompt Restrictions
Each agent prompt must include:
```
CONSTRAINTS:
- ABSOLUTELY FORBIDDEN: Never modify the pipeline configuration (.gitlab-ci.yml)
- If pipeline fails: Debug and fix CODE/TESTS only, never the pipeline itself
- If you encounter pipeline issues: Report them, don't fix them
```

### 2. System Validation
- Pipeline changes should be rejected if made by agents
- System should detect and revert unauthorized pipeline modifications
- Supervisor should enforce agent boundaries

### 3. Monitoring
- Track when agents attempt to modify pipelines
- Log violations of scope boundaries
- Alert when agents exceed their authority

## Summary
The key principle is: **Agents work ON the code, not the infrastructure**. They must solve problems within their domain rather than changing the rules to avoid problems. This ensures:
1. Consistent, comparable pipelines for research
2. Proper problem resolution rather than avoidance
3. Clear separation of concerns
4. Reliable system behavior