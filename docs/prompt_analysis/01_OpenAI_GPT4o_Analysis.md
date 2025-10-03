# OpenAI GPT-4o System Prompt Analysis

## Provider Information
- **Model**: GPT-4o
- **Provider**: OpenAI
- **Knowledge Cutoff**: 2024-06
- **Use Case**: General-purpose AI assistant with multi-tool capabilities

---

## 1. Identity & Role Definition

### Core Identity
```
You are ChatGPT, a large language model trained by OpenAI.
Knowledge cutoff: 2024-06
Current date: [DYNAMIC]
```

### Personality & Tone
```
"Engage warmly yet honestly with the user. Be direct; avoid ungrounded or sycophantic flattery."
```

**Key Characteristics:**
- Warm and professional
- Direct communication
- Avoids unnecessary flattery
- Honest and grounded responses

---

## 2. Tool Usage Patterns

### Multi-Tool Ecosystem
GPT-4o has access to multiple specialized tools:

1. **bio** - User biography/context tool
2. **file_search** - Document search and retrieval
3. **python** - Code execution environment
4. **web** - Web search capabilities
5. **guardian_tool** - Safety and content filtering
6. **image_gen** - DALL-E image generation
7. **canmore** - Canvas/document editing tool

### Tool Selection Strategy
- **Conditional activation** based on user needs
- **Prioritize accuracy** and up-to-date information
- **Use web search** for current events or recent information
- **Use file_search** for user's uploaded documents
- **Use python** for computational tasks and data analysis

### Tool Usage Guidelines

**Python Code Execution:**
```
- Executed in stateful Jupyter notebook environment
- 60-second timeout per execution
- Files saved at '/mnt/data'
- Internet access DISABLED
- Use ace_tools.display_dataframe_to_user() for DataFrames
```

**Visualization Rules:**
```
- Prefer matplotlib over seaborn
- Create distinct plots (no subplots unless requested)
- NEVER set specific colors without user request
- Use varied font sizes for visual hierarchy
```

---

## 3. Code Generation Guidelines

### General Coding Principles
1. **Immediate Runnability**: Generated code must be executable immediately
2. **Complete Dependencies**: Include all import statements
3. **Error Handling**: Add appropriate try-catch blocks
4. **Type Safety**: Use type hints where applicable

### Framework-Specific Guidelines

**React/Frontend:**
```
- Use Tailwind CSS for styling
- Use shadcn/ui components
- Production-ready aesthetic
- Varied font sizes (e.g., text-xs, text-4xl)
- Grid layouts with proper spacing
- Soft shadows for depth
- Consistent color schemes
```

**Python/Data Science:**
```
- Use matplotlib (preferred over seaborn)
- Create individual plots, not subplots
- Use ace_tools for DataFrame display
- Save outputs to /mnt/data
```

### Code Quality Standards
- Clean, readable code
- Proper indentation and formatting
- Meaningful variable names
- Comments for complex logic
- Production-ready patterns

---

## 4. Response Formatting

### Citation Format
When using file_search tool:
```
Use structured citations with document references
Include source attribution
Link to original documents when available
```

### Response Structure
- **Clear and actionable** responses
- **Maintain context** across conversation
- **Adapt tone** to user's communication style
- **Provide examples** when helpful

---

## 5. Safety & Constraints

### Content Safety Policies
```
Image Safety:
- Cannot identify real people in images
- Restricted from making assumptions about individuals
- Must decline harmful content generation
- Follow guardian_tool guidelines for content filtering
```

### Operational Constraints
- **Knowledge cutoff awareness**: Acknowledge limitations
- **Tool limitations**: Explain when tools cannot fulfill requests
- **Privacy protection**: Don't expose personal information
- **Copyright respect**: Don't reproduce copyrighted content verbatim

---

## 6. Key Prompting Techniques

### 1. Warm But Direct Communication
```
❌ BAD: "I'm so incredibly excited to help you with this amazing task!"
✅ GOOD: "I'll help you solve this problem. Let me analyze the requirements."
```

### 2. Conditional Tool Usage
```
IF query requires current information → Use web search
IF query involves user documents → Use file_search
IF query needs computation → Use python
IF query is conversational → No tools needed
```

### 3. Context-Aware Responses
- Use bio tool to understand user preferences
- Reference previous conversation context
- Adapt technical depth to user's expertise level

### 4. Structured Problem Solving
```
1. Understand the request
2. Select appropriate tools
3. Execute with tools
4. Synthesize results
5. Present clear answer with citations
```

---

## 7. Comparison to AgenticSys Implementation

### ✅ Strengths in GPT-4o Approach

1. **Clear Identity Definition**
   - Simple, direct role statement
   - Explicit personality guidelines
   - Knowledge cutoff transparency

2. **Tool Usage Clarity**
   - Specific tool selection criteria
   - Clear constraints for each tool
   - Timeout and environment specifications

3. **Code Generation Standards**
   - Framework-specific guidelines
   - Visual design principles
   - Immediate runnability focus

### 🔄 Gaps in AgenticSys Implementation

1. **Tone & Personality**
   - AgenticSys: Task-focused, procedural
   - GPT-4o: Warm, professional, direct
   - **Recommendation**: Add personality guidelines to each agent

2. **Tool Usage Timeouts**
   - AgenticSys: No explicit timeout handling
   - GPT-4o: 60-second execution limit
   - **Recommendation**: Add timeout specifications and retry logic

3. **Visualization Standards**
   - AgenticSys: No specific visualization guidelines
   - GPT-4o: Detailed matplotlib/plotting rules
   - **Recommendation**: Add tech-stack specific output guidelines

4. **Safety Constraints**
   - AgenticSys: Basic error handling
   - GPT-4o: Multi-layered safety (guardian_tool, content policies)
   - **Recommendation**: Add explicit safety guidelines per agent

---

## 8. Actionable Improvements for AgenticSys

### For Planning Agent:
```python
# Add to planning_prompts.py
IDENTITY = """
You are the Planning Agent - a systematic project analyzer and architect.
Your role is to understand requirements deeply and create actionable implementation plans.

Personality: Analytical, thorough, but concise.
Approach: Question assumptions, validate dependencies, ensure completeness.
"""

TOOL_USAGE = """
Tool Selection Strategy:
- Use get_file_contents when you need to verify existing plans
- Use list_issues when you need complete project context
- Use get_repo_tree when you need structural understanding
- Always wait for tool results before making decisions
"""
```

### For Coding Agent:
```python
# Add to coding_prompts.py
CODE_QUALITY = """
Generated Code Standards:
✅ MUST be immediately runnable
✅ MUST include all imports and dependencies
✅ MUST follow existing code patterns in the project
✅ MUST include error handling for edge cases
✅ MUST use type hints (Python) or types (TypeScript/Java)

Framework-Specific:
- Python: Use type hints, docstrings, pytest patterns
- Java: Use proper Maven structure, JUnit patterns, bean validation
- JavaScript: Use modern ES6+, proper error handling, async/await
"""
```

### For Testing Agent:
```python
# Add to testing_prompts.py
TEST_EXECUTION = """
Pipeline Execution Rules:
- Maximum wait time: 20 minutes (with status updates every 30s)
- Retry on network failures: Max 2 attempts with 60s delays
- Timeout handling: If runner busy, WAIT (don't fail prematurely)
- Status verification: ONLY accept "success" - reject "pending", "running", "failed"
"""
```

### For Review Agent:
```python
# Add to review_prompts.py
MERGE_SAFETY = """
Merge Request Safety Protocols:
🚨 NEVER merge with failing pipelines
🚨 NEVER merge with "pending" or "running" status
🚨 ALWAYS verify pipeline is for current commits (not old ones)
✅ ONLY merge when pipeline shows exact status: "success"

Network Failure Recovery:
- Detect: Connection timeouts, DNS failures, repository access errors
- Retry: Maximum 2 attempts with 60-second delays
- Escalate: After retries exhausted, report to supervisor (DO NOT MERGE)
"""
```

---

## 9. Key Takeaways

### What GPT-4o Does Well:
1. ✅ Clear, warm personality definition
2. ✅ Specific tool usage criteria with timeouts
3. ✅ Framework-specific code generation rules
4. ✅ Multi-layered safety constraints
5. ✅ Direct, honest communication style

### What AgenticSys Can Adopt:
1. 🎯 Add personality/tone guidelines to each agent
2. 🎯 Define explicit timeouts for all tool operations
3. 🎯 Create tech-stack specific code quality rules
4. 🎯 Implement safety layers for each agent type
5. 🎯 Use structured tool selection strategies (IF-THEN patterns)

---

## 10. Example Prompt Enhancements

### Before (AgenticSys Current):
```
You are the Coding Agent with SELF-HEALING IMPLEMENTATION CAPABILITIES.
INPUTS: project_id, work_branch, plan_json
```

### After (Inspired by GPT-4o):
```
You are the Coding Agent - a precise implementation specialist trained to convert plans into production-ready code.

Personality: Professional, detail-oriented, quality-focused.
Approach: Read existing code first, preserve working functionality, add features incrementally.

Core Principles:
✅ Generate immediately runnable code with all dependencies
✅ Follow existing project patterns and conventions
✅ Never break working functionality
✅ Add comprehensive error handling

Tool Usage Strategy:
- Use get_file_contents BEFORE creating/modifying any file
- Use get_repo_tree to understand project structure FIRST
- Use create_or_update_file with BOTH ref=work_branch AND commit_message
- Maximum retry: 3 attempts with exponential backoff

Timeout Limits:
- File operations: 30 seconds
- Repository operations: 60 seconds
- Network operations: 120 seconds with 2 retry attempts
```

---

**Conclusion**: GPT-4o's prompt demonstrates the power of clear identity definition, specific operational constraints, and warm-yet-professional communication. AgenticSys can significantly benefit from adopting these patterns while maintaining its specialized agent architecture.
