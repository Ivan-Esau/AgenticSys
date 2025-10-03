# AgenticSys Prompt Architecture Design

## Overview

This document defines the hierarchical prompt structure for AgenticSys, implementing inheritance patterns from base prompts to role-specific prompts.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      BASE_PROMPTS.PY                        │
│  Universal patterns inherited by ALL agents                 │
│  - Identity foundation                                      │
│  - Communication standards                                  │
│  - Tool usage discipline                                    │
│  - Safety & ethical constraints                             │
│  - Response optimization                                    │
│  - Verification protocols                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   PLANNING_PROMPTS.PY     │   │   CODING_PROMPTS.PY       │
│   + Project analysis      │   │   + Implementation        │
│   + Dependency resolution │   │   + File operations       │
│   + Multi-solution eval   │   │   + Code quality          │
│   + Structure creation    │   │   + Language-specific     │
└───────────────────────────┘   └───────────────────────────┘
                │                           │
                ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   TESTING_PROMPTS.PY      │   │   REVIEW_PROMPTS.PY       │
│   + Test creation         │   │   + MR creation           │
│   + Pipeline monitoring   │   │   + Pipeline verification │
│   + Self-healing tests    │   │   + Merge safety          │
│   + Coverage analysis     │   │   + Issue closure         │
└───────────────────────────┘   └───────────────────────────┘
```

---

## Inheritance Pattern

### Base Prompt (100% inherited by all)
```python
BASE_PROMPT = f"""
{IDENTITY_FOUNDATION}
{COMMUNICATION_STANDARDS}
{TOOL_USAGE_DISCIPLINE}
{SAFETY_CONSTRAINTS}
{RESPONSE_OPTIMIZATION}
{VERIFICATION_PROTOCOLS}
"""

# Each role-specific prompt
ROLE_PROMPT = f"""
{BASE_PROMPT}

{ROLE_SPECIFIC_IDENTITY}
{ROLE_SPECIFIC_WORKFLOW}
{ROLE_SPECIFIC_TOOLS}
{ROLE_SPECIFIC_CONSTRAINTS}
{ROLE_SPECIFIC_COMPLETION}
"""
```

---

## Base Prompt Components

### 1. Identity Foundation (Universal)
```
- Agent ecosystem awareness
- Professional personality traits
- Core principles (verify-implement-confirm)
- Ethical constraints
```

### 2. Communication Standards (Universal)
```
- Conciseness guidelines (match detail to complexity)
- Response verbosity levels (simple → complex)
- No preamble/postamble rules
- Status update formats
```

### 3. Tool Usage Discipline (Universal)
```
- Tool selection strategy (IF-THEN patterns)
- Forbidden operations (NEVER use bash for files)
- Timeout specifications (30s, 60s, 120s)
- Parallel execution patterns
- Retry logic (max 3 attempts)
```

### 4. Safety & Ethical Constraints (Universal)
```
- Malicious intent filter
- Secret protection
- Git safety protocols
- Pipeline safety rules
- Data preservation rules
```

### 5. Response Optimization (Universal)
```
- Token minimization
- Direct answers for simple queries
- Detailed responses for complex tasks
- Error reporting with remediation
```

### 6. Verification Protocols (Universal)
```
- Zero-assumption principle
- Read-before-edit enforcement
- File existence verification
- Branch state verification
- Pipeline currency verification
```

---

## Role-Specific Extensions

### Planning Agent Extensions
```
+ Project context gathering (parallel tool execution)
+ Dependency analysis from issue descriptions
+ Multi-solution evaluation with trade-offs
+ ORCH_PLAN.json creation with topological sort
+ Foundation structure creation
+ Temporal awareness (latest best practices)
```

### Coding Agent Extensions
```
+ Implementation workflow (read → analyze → implement → verify)
+ Language detection and matching
+ Framework-specific standards (Python/Java/JS)
+ Code quality requirements
+ Dependency management
+ Input classification (question vs task vs debug)
```

### Testing Agent Extensions
```
+ Test creation strategies (unit/integration/e2e)
+ Pipeline monitoring protocol (YOUR pipeline only)
+ Self-healing test debugging (max 3 attempts)
+ Network failure retry logic
+ Coverage analysis
+ Test quality standards
```

### Review Agent Extensions
```
+ MR creation with comprehensive context
+ Pipeline verification (current pipeline only)
+ Merge safety protocols (NEVER on failure)
+ Network failure handling with retries
+ Issue closure workflow
+ Branch cleanup
```

---

## File Structure

```
src/agents/prompts/
├── __init__.py
├── base_prompts.py              # NEW: Universal base for all agents
├── prompt_templates.py          # KEEP: Tech-stack specific templates
├── config_utils.py              # KEEP: Configuration helpers
├── gitlab_tips.py               # KEEP: GitLab-specific guidance
├── planning_prompts.py          # UPDATE: Import from base_prompts
├── coding_prompts.py            # UPDATE: Import from base_prompts
├── testing_prompts.py           # UPDATE: Import from base_prompts
└── review_prompts.py            # UPDATE: Import from base_prompts
```

---

## Implementation Strategy

### Phase 1: Create Base Prompts (base_prompts.py)
```python
# Core components that ALL agents inherit

def get_base_prompt(agent_name: str, agent_role: str) -> str:
    """Generate base prompt inherited by all agents."""
    return f"""
{get_identity_foundation(agent_name, agent_role)}
{get_communication_standards()}
{get_tool_usage_discipline()}
{get_safety_constraints()}
{get_response_optimization()}
{get_verification_protocols()}
"""
```

### Phase 2: Update Role-Specific Prompts
```python
# In planning_prompts.py
from .base_prompts import get_base_prompt

def get_planning_prompt(pipeline_config=None):
    base = get_base_prompt("Planning Agent", "systematic project analyzer and architect")

    return f"""
{base}

{get_planning_specific_workflow()}
{get_planning_tools()}
{get_planning_constraints()}
{get_planning_completion()}
"""
```

### Phase 3: Modular Component Design
```python
# Each component is independently testable and maintainable

def get_identity_foundation(agent_name: str, role: str) -> str:
    """Universal identity pattern for all agents."""

def get_communication_standards() -> str:
    """Universal communication guidelines."""

def get_tool_usage_discipline() -> str:
    """Universal tool selection and usage patterns."""
```

---

## Benefits of This Architecture

### ✅ Consistency
- All agents share same base principles
- Uniform communication standards
- Consistent safety constraints

### ✅ Maintainability
- Update base prompt → All agents inherit changes
- Role-specific changes isolated to role files
- Clear separation of concerns

### ✅ Testability
- Test base components independently
- Test role-specific additions separately
- Validate inheritance properly

### ✅ Scalability
- Easy to add new agents (inherit from base)
- Easy to add new base patterns (all agents get them)
- Easy to override base patterns per role if needed

### ✅ Documentation
- Clear hierarchy in code
- Self-documenting structure
- Easy to understand agent capabilities

---

## Example: Complete Agent Prompt

```python
# Final assembled prompt for Coding Agent

BASE (inherited):
- Identity: "You are part of AgenticSys, a multi-agent system..."
- Communication: "Simple queries → Simple answers..."
- Tool usage: "Use get_file_contents for reading (NEVER bash cat)..."
- Safety: "🚨 NEVER assist with malicious intent..."
- Response: "Match detail level to task complexity..."
- Verification: "NEVER assume file exists - verify with get_file_contents..."

ROLE-SPECIFIC (Coding Agent):
- Identity: "You are the Coding Agent - implementation specialist..."
- Workflow: "1) Read files 2) Analyze patterns 3) Implement 4) Verify..."
- Tools: "Python: type hints, Java: bean validation, JS: TypeScript..."
- Constraints: "NEVER modify tests, NEVER create MRs..."
- Completion: "CODING_PHASE_COMPLETE: Issue #X implementation finished..."
```

---

## Prompt Composition Pattern

```python
def compose_prompt(base: str, extensions: List[str]) -> str:
    """
    Compose final prompt from base + extensions.

    Args:
        base: Base prompt (universal)
        extensions: List of role-specific extensions

    Returns:
        Complete assembled prompt
    """
    sections = [base] + extensions
    return "\n\n".join(sections)
```

---

## Version Control & Updates

### Base Prompt Updates
- Version: Track in base_prompts.py docstring
- Changes: Document in CHANGELOG
- Impact: All agents inherit changes
- Testing: Run full agent test suite

### Role Prompt Updates
- Version: Track in role-specific file docstring
- Changes: Document inline
- Impact: Only specific agent affected
- Testing: Run agent-specific tests

---

## Migration Plan

### Step 1: Create base_prompts.py
- Extract universal patterns from existing prompts
- Organize into modular components
- Add comprehensive docstrings

### Step 2: Update planning_prompts.py
- Import base components
- Add planning-specific extensions
- Test Planning Agent behavior

### Step 3: Update coding_prompts.py
- Import base components
- Add coding-specific extensions
- Test Coding Agent behavior

### Step 4: Update testing_prompts.py
- Import base components
- Add testing-specific extensions
- Test Testing Agent behavior

### Step 5: Update review_prompts.py
- Import base components
- Add review-specific extensions
- Test Review Agent behavior

### Step 6: Validate & Test
- Run all agents end-to-end
- Verify no regressions
- Document improvements

---

## Success Criteria

### ✅ Code Quality
- No duplication across prompt files
- Clear inheritance hierarchy
- Comprehensive docstrings
- Type hints for all functions

### ✅ Agent Behavior
- All agents exhibit consistent base behaviors
- Role-specific behaviors work correctly
- No regressions from current implementation
- Improved quality metrics (measured)

### ✅ Developer Experience
- Easy to understand prompt structure
- Easy to add new agents
- Easy to update base patterns
- Clear documentation

---

## Next Steps

1. ✅ Review and approve this architecture
2. ⏳ Implement base_prompts.py with all universal components
3. ⏳ Update planning_prompts.py with inheritance
4. ⏳ Update coding_prompts.py with inheritance
5. ⏳ Update testing_prompts.py with inheritance
6. ⏳ Update review_prompts.py with inheritance
7. ⏳ Test all agents with enhanced prompts
8. ⏳ Measure improvements vs current implementation

---

**Status**: Design Complete - Ready for Implementation
**Last Updated**: 2025-10-03
**Designed by**: Claude Code (Anthropic)
