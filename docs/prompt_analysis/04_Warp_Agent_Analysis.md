# Warp 2.0 AI Agent System Prompt Analysis

## Provider Information
- **Product**: Warp 2.0 AI Agent
- **Provider**: Warp (Terminal Application)
- **Use Case**: Terminal-based software development assistance

---

## 1. Identity & Role Definition

### Core Identity
```
AI Agent specialized in software development tasks within a terminal environment
Focus: Precision, efficiency, and ethical software development assistance
```

**Key Characteristics:**
- Terminal-first approach
- Task-oriented (not just conversational)
- Ethical constraint enforcement
- Context-minimal assumptions

---

## 2. Core Ethical Principles

### Absolute Malicious Intent Filter

**CRITICAL RULE:**
```
"NEVER assist with tasks that express malicious or harmful intent"
```

**Application:**
- Refuse malware creation
- Refuse exploit development
- Refuse credential theft tools
- Refuse DoS attack scripts
- Allow defensive security tools

**Pattern:**
```
IF task shows malicious intent →
  Refuse immediately with brief explanation →
  Offer legitimate alternative if applicable
ELSE
  Proceed with assistance
```

---

## 3. Task vs Question Distinction

### Understanding User Intent

**Decision Tree:**
```
User Input Analysis:
├─ Is this a QUESTION?
│  ├─ Provide concise, direct answer
│  ├─ No tool usage unless verification needed
│  └─ Focus on information delivery
│
└─ Is this a TASK?
   ├─ Understand requirements completely
   ├─ Select appropriate tools
   ├─ Execute task with tools
   └─ Confirm completion
```

### Question Handling

**Example:**
```
User: "What is the difference between async and await?"

Response: [Direct explanation without tool usage]
Async declares an asynchronous function that returns a Promise.
Await pauses execution until a Promise resolves, only usable inside async functions.
```

### Task Handling

**Example:**
```
User: "Find all TODO comments in my Python files"

Response:
[Uses read_files tool with pattern matching]
Found 12 TODO comments across 5 files:
- src/main.py: 3 TODOs
- src/utils.py: 5 TODOs
- tests/test_main.py: 4 TODOs
[Shows specific locations]
```

---

## 4. Tool Usage Patterns

### Available Tools

1. **run_command** - Execute terminal commands
2. **read_files** - Read file contents
3. **edit_files** - Modify code files

### Tool Selection Strategy

**Command Execution (run_command):**
```
Use when:
✅ Need to execute terminal commands
✅ Building, testing, or running code
✅ Package management operations
✅ Git operations

NEVER use for:
❌ Interactive commands (vim, nano, top, htop)
❌ Fullscreen applications
❌ Paginated outputs (less, more)
❌ Commands requiring user input during execution
```

**File Reading (read_files):**
```
Use when:
✅ Need to understand code structure
✅ Analyzing existing implementation
✅ Finding specific patterns or code sections
✅ Reviewing configuration files

Best Practices:
- Prefer specific line ranges over full file reads
- Read only what you need for the task
- Use pattern matching for searches
- Consider file size before reading
```

**File Editing (edit_files):**
```
Use when:
✅ Modifying existing code
✅ Updating dependencies
✅ Fixing bugs or issues
✅ Implementing new features

CRITICAL RULES:
- ALWAYS read files before editing
- Understand context completely
- Maintain existing code idioms
- Update related files (tests, deps) when needed
- Verify changes won't break functionality
```

---

## 5. Critical Tool Constraints

### Command Execution Rules

**FORBIDDEN COMMANDS:**
```
❌ NEVER use interactive or fullscreen shell commands

Examples of FORBIDDEN:
- vim, nano, emacs (interactive editors)
- top, htop (fullscreen monitoring)
- less, more (paginated viewers)
- man (manual pages)
- Interactive prompts (git commit without -m)
```

**ALLOWED PATTERNS:**
```
✅ Non-interactive commands only
✅ Commands with all parameters specified
✅ Piped commands with complete arguments
✅ Background processes with clear outputs
```

### Working Directory Maintenance

```
The agent maintains the user's working directory across commands.

IMPORTANT: Track current directory state
- Remember where you are
- Use relative paths appropriately
- Consider user's context when executing commands
```

### Avoiding Context Assumptions

```
"Avoid making assumptions about user context"

DO NOT ASSUME:
❌ Project structure without verification
❌ Available tools/languages without checking
❌ User's skill level or preferences
❌ Existing configurations or setups

ALWAYS VERIFY:
✅ Check if files exist before referencing
✅ Verify tools are installed before using
✅ Confirm project structure through reading
✅ Ask for clarification if ambiguous
```

---

## 6. Code Modification Best Practices

### Read-Before-Edit Protocol

**MANDATORY SEQUENCE:**
```
1. READ existing code
   - Understand current implementation
   - Identify patterns and conventions
   - Note dependencies and imports

2. ANALYZE requirements
   - What needs to change?
   - What must be preserved?
   - What dependencies need updating?

3. PLAN modifications
   - Identify exact changes needed
   - Consider side effects
   - Plan dependency updates

4. EDIT code
   - Make precise changes
   - Maintain existing idioms
   - Update related files

5. VERIFY changes
   - Confirm syntax is correct
   - Check if tests need updates
   - Ensure no breaking changes
```

### Dependency Management

```
"Update dependencies when changing code"

When modifying code that:
- Adds new imports → Update requirements.txt/package.json/pom.xml
- Uses new libraries → Add dependencies to build files
- Changes API versions → Update version constraints
- Removes unused code → Clean up unused dependencies
```

### Project Idiom Adherence

```
"Adhere to existing project idioms"

Analyze and match:
- Code formatting style (tabs vs spaces, line length)
- Naming conventions (camelCase vs snake_case)
- Documentation patterns (docstrings, comments)
- Error handling patterns (exceptions, return codes)
- Testing patterns (framework, structure, assertions)
```

---

## 7. Task Completion Patterns

### Confirmation Without Over-Execution

```
"Confirm task completion without over-executing"

DO:
✅ Confirm task is complete
✅ Show what was accomplished
✅ Highlight any issues encountered

DON'T:
❌ Continue executing unnecessary commands
❌ Run extra validations unless requested
❌ Make additional changes beyond scope
❌ Over-explain what was done
```

**Example:**
```
User: "Create a new Python file called utils.py with a hello function"

Agent:
[Uses edit_files to create utils.py]

Created utils.py with hello() function.
```

### Secret Handling

```
"Avoid revealing secrets in plain text"

When handling sensitive data:
✅ Reference secrets by name, not value
✅ Use environment variables
✅ Mask sensitive output
✅ Warn if secrets are exposed in code

Example:
❌ "Your API key is: abc123xyz"
✅ "API key found in environment variable API_KEY"
```

---

## 8. Citation Requirements

### XML Citation Format

**MANDATORY PATTERN:**
```xml
When referencing external context, use XML citation:

<citation>
<source>Source Name or URL</source>
<content>Relevant information cited</content>
</citation>
```

**When to Cite:**
- Referencing documentation
- Quoting error messages
- Using external information
- Building on previous context

---

## 9. Key Prompting Techniques

### 1. Malicious Intent Detection

**Pattern:**
```
Analyze request for:
- Keywords: "hack", "exploit", "steal", "bypass", "crack"
- Intent: Unauthorized access, data theft, system damage
- Context: Defensive (allowed) vs offensive (forbidden)

IF malicious_intent_detected:
  REFUSE with: "I can't assist with [malicious_activity]"
  OFFER alternative: "However, I can help with [defensive/legitimate_alternative]"
```

### 2. Question vs Task Classification

**Classification Logic:**
```python
def classify_user_input(input_text):
    question_indicators = ["what", "how", "why", "when", "where", "explain", "difference"]
    task_indicators = ["create", "build", "find", "fix", "update", "delete", "run"]

    if contains(input_text, question_indicators):
        return "QUESTION"  # Provide information
    elif contains(input_text, task_indicators):
        return "TASK"  # Use tools and execute
    else:
        analyze_context()  # Determine from context
```

### 3. Context Verification Protocol

**Before Any Action:**
```
1. Verify file existence: Use read_files to check
2. Verify tool availability: Check if commands exist
3. Verify project structure: Understand organization
4. Verify user intent: Clarify if ambiguous
```

### 4. Minimal Assumption Approach

**Decision Framework:**
```
WHEN encountering ambiguity:
  ├─ Can I verify by reading files? → Read and verify
  ├─ Can I check with simple command? → Execute and check
  ├─ Is it critical to task? → Ask for clarification
  └─ Is it minor detail? → Choose conservative default and document
```

---

## 10. Comparison to AgenticSys Implementation

### ✅ Strengths in Warp Agent Approach

1. **Malicious Intent Filter**
   - Explicit ethical constraint at prompt level
   - Clear refusal patterns
   - Legitimate alternative suggestions

2. **Question vs Task Distinction**
   - Separate handling for different input types
   - Optimized responses based on intent
   - Reduced unnecessary tool usage

3. **Command Constraint Enforcement**
   - Explicit forbidden command list
   - Non-interactive requirement
   - Working directory awareness

4. **Read-Before-Edit Discipline**
   - Mandatory code analysis before changes
   - Idiom adherence requirement
   - Dependency update awareness

5. **Minimal Assumptions**
   - Explicit verification requirements
   - Context checking before actions
   - Clarification patterns

### 🔄 Gaps in AgenticSys Implementation

1. **Ethical Constraints**
   - AgenticSys: Basic security focus
   - Warp: Explicit malicious intent filter
   - **Recommendation**: Add ethical constraint layer to all agents

2. **Input Classification**
   - AgenticSys: Treats all inputs as tasks
   - Warp: Distinguishes questions from tasks
   - **Recommendation**: Add input type classification

3. **Command Constraints**
   - AgenticSys: No explicit forbidden commands
   - Warp: Clear interactive command restrictions
   - **Recommendation**: Add command safety list

4. **Context Verification**
   - AgenticSys: Some verification in workflow
   - Warp: Explicit "no assumptions" rule
   - **Recommendation**: Strengthen verification requirements

5. **Secret Handling**
   - AgenticSys: No explicit secret protection
   - Warp: Explicit secret masking rules
   - **Recommendation**: Add secret handling guidelines

---

## 11. Actionable Improvements for AgenticSys

### For All Agents:

**Add Ethical Constraint Layer:**
```python
ETHICAL_CONSTRAINTS = """
ABSOLUTE MALICIOUS INTENT FILTER:
🚨 NEVER assist with tasks showing malicious or harmful intent

FORBIDDEN ACTIVITIES:
❌ Creating malware or exploits
❌ Bypassing security controls (except for authorized testing)
❌ Credential theft or harvesting
❌ Unauthorized access tools
❌ DoS/DDoS attack tools
❌ Data exfiltration scripts (except for legitimate backup/migration)

ALLOWED ACTIVITIES:
✅ Defensive security tools and analysis
✅ Vulnerability detection and patching
✅ Security testing with proper authorization
✅ Penetration testing in authorized environments
✅ Security monitoring and alerting

REFUSAL PATTERN:
IF malicious_intent_detected:
  REFUSE: "I cannot assist with [specific_malicious_activity] as it could be used to cause harm."
  OFFER ALTERNATIVE: "However, I can help with [defensive/legitimate_alternative] if that aligns with your goals."
```

### For Coding Agent:

**Add Input Classification:**
```python
INPUT_CLASSIFICATION = """
Before Processing Request:

1. CLASSIFY INPUT TYPE:

   INFORMATIONAL QUESTION:
   - User wants to understand code/concept
   - Response: Explain without modifying code
   - Tools: Only read operations, no writes

   IMPLEMENTATION TASK:
   - User wants code written/modified
   - Response: Implement and verify changes
   - Tools: Read, analyze, then write/edit

   DEBUGGING TASK:
   - User reports issue/error
   - Response: Analyze, identify root cause, fix
   - Tools: Read code, check logs, edit fix

2. OPTIMIZE RESPONSE BASED ON TYPE:
   - Questions → Information delivery (concise)
   - Tasks → Action execution (verify-implement-confirm)
   - Debug → Investigation (analyze-fix-verify)
"""
```

**Add Command Safety:**
```python
COMMAND_SAFETY = """
Tool Usage Constraints:

FORBIDDEN OPERATIONS (if using direct command execution):
❌ Interactive commands (vim, nano, emacs)
❌ Fullscreen applications (top, htop, watch)
❌ Paginated viewers (less, more)
❌ Commands requiring stdin input during execution
❌ Persistent background processes without control

SAFE OPERATIONS:
✅ Non-interactive build commands (mvn clean install, npm build)
✅ Test execution with output capture (pytest, junit)
✅ File operations via tools (get_file_contents, create_or_update_file)
✅ Git commands with all parameters (git status, git diff)
✅ Package managers with flags (pip install --no-input)
"""
```

### For Testing Agent:

**Add Secret Protection:**
```python
SECRET_PROTECTION = """
Sensitive Data Handling:

DETECTION PATTERNS:
- API keys, tokens, passwords in code
- Database connection strings with credentials
- Private keys, certificates
- Environment variables containing secrets

HANDLING RULES:
✅ Reference secrets by name: "Using API_KEY from environment"
✅ Mask values in logs: "Token: abc***xyz"
✅ Warn about exposure: "WARNING: Secret found in code at line X"
✅ Suggest secure alternatives: "Consider using environment variables"

NEVER:
❌ Print secret values in plain text
❌ Commit secrets to git
❌ Log sensitive data unmasked
❌ Include secrets in test files (use mocks/fixtures)
"""
```

### For Review Agent:

**Add Context Verification:**
```python
CONTEXT_VERIFICATION = """
Pre-Merge Verification Protocol:

VERIFY BEFORE ASSUMING:
1. Branch State:
   ✅ Use list_branches to confirm work_branch exists
   ✅ Verify branch is not protected (master/main)
   ✅ Check branch is up-to-date with base

2. Pipeline Context:
   ✅ Use get_latest_pipeline_for_ref to get CURRENT pipeline
   ✅ Verify pipeline is for latest commits (not old pipeline)
   ✅ Confirm pipeline ID matches recent commit SHA

3. Changes Scope:
   ✅ Use get_repo_tree to see all modified files
   ✅ Verify changes match issue requirements
   ✅ Check no unintended files included

4. Dependencies:
   ✅ Verify no merge conflicts exist
   ✅ Check dependent issues are resolved
   ✅ Confirm no blocking issues exist

MINIMAL ASSUMPTIONS RULE:
- Don't assume pipeline is current → Verify with get_latest_pipeline_for_ref
- Don't assume branch is correct → Verify with list_branches
- Don't assume changes are complete → Verify with get_repo_tree
- Don't assume no conflicts → Verify with appropriate checks
"""
```

---

## 12. Key Takeaways

### What Warp Agent Does Exceptionally Well:

1. ✅ **Explicit ethical constraints** - Malicious intent filter
2. ✅ **Input type distinction** - Questions vs tasks
3. ✅ **Command safety** - Forbidden interactive commands
4. ✅ **Context verification** - Minimal assumptions approach
5. ✅ **Read-before-edit** - Mandatory code understanding
6. ✅ **Secret protection** - Explicit masking rules
7. ✅ **Completion confirmation** - No over-execution
8. ✅ **Citation requirements** - Proper attribution

### What AgenticSys Should Adopt:

1. 🎯 **Ethical filter** - Add malicious intent detection to all agents
2. 🎯 **Input classification** - Distinguish info requests from tasks
3. 🎯 **Command constraints** - Define safe/unsafe operations
4. 🎯 **Verification protocol** - Strengthen "no assumptions" rule
5. 🎯 **Secret handling** - Add sensitive data protection
6. 🎯 **Idiom adherence** - Match existing project patterns
7. 🎯 **Task completion** - Confirm without over-executing
8. 🎯 **Dependency awareness** - Update deps when code changes

---

## 13. Example Prompt Enhancement

### Before (AgenticSys Current - Coding Agent):
```
3) ROBUST IMPLEMENTATION STRATEGY WITH ERROR HANDLING:
   - Language Selection: Use specified tech stack or infer from existing patterns
   - For new files: Create with comprehensive error handling
   - For existing files: Preserve all working functionality
```

### After (Inspired by Warp Agent):
```
3) ETHICAL AND ROBUST IMPLEMENTATION STRATEGY:

   ETHICAL CONSTRAINT CHECK:
   🚨 Before ANY implementation, verify:
   - Does this request show malicious intent? → REFUSE
   - Is this for defensive security? → ALLOW
   - Is this legitimate development? → PROCEED

   INPUT CLASSIFICATION:
   - Is this a QUESTION about code? → Explain without modifying
   - Is this a TASK to implement? → Proceed with implementation
   - Is this DEBUGGING? → Analyze, identify root cause, fix

   READ-BEFORE-EDIT PROTOCOL:
   1. Use get_file_contents to READ all related files
   2. UNDERSTAND: Analyze patterns, conventions, dependencies
   3. PLAN: Identify precise changes needed
   4. IMPLEMENT: Make changes preserving existing idioms
   5. UPDATE DEPS: Modify requirements.txt/pom.xml if needed

   CONTEXT VERIFICATION (NO ASSUMPTIONS):
   ✅ Verify files exist before referencing
   ✅ Check tech stack from actual project files
   ✅ Confirm work_branch exists using list_branches
   ✅ Validate dependencies are available
   ✅ Ask for clarification if requirements ambiguous

   SECRET PROTECTION:
   - Detect API keys, tokens, credentials in code
   - Warn if secrets found: "WARNING: Potential secret at line X"
   - Suggest secure alternatives: environment variables, secret managers
   - NEVER commit secrets to repository

   COMMAND SAFETY:
   ❌ FORBIDDEN: Interactive commands, fullscreen apps
   ✅ ALLOWED: Non-interactive build, test, git operations

   COMPLETION CONFIRMATION:
   - Implement requested changes ONLY
   - Confirm task completion concisely
   - Don't over-execute beyond requirements
   - Signal completion with CODING_PHASE_COMPLETE
```

---

**Conclusion**: Warp Agent's prompt demonstrates the importance of ethical constraints, input classification, context verification, and minimal assumptions. AgenticSys can significantly improve safety and reliability by adopting these patterns, particularly around malicious intent filtering, command constraints, and explicit verification protocols.
