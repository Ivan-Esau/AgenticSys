# Single Model vs Task-Specific Models

## Question
When selecting a model in the GUI (e.g., "openai/gpt-4"), is this ONE model used for ALL agents (Planning, Coding, Testing, Review)?

## Answer: YES, Currently One Model for All Agents

### Current Behavior

```
GUI Selection: openai/gpt-4
         ↓
    Config.LLM_MODEL = "gpt-4"
    Config.LLM_PROVIDER = "openai"
    Config.LLM_TEMPERATURE = 0.7
         ↓
    ┌─────────────────────────────────────┐
    │ ALL AGENTS USE SAME MODEL:          │
    │ - Planning Agent  → gpt-4           │
    │ - Coding Agent    → gpt-4           │
    │ - Testing Agent   → gpt-4           │
    │ - Review Agent    → gpt-4           │
    └─────────────────────────────────────┘
```

### Code Flow

#### 1. Agent Creation (`src/agents/utils/agent_factory.py`)

All agent factories call the same `create_agent()` function with `model=None`:

```python
def create_planning_agent(tools, project_id, pipeline_config, output_callback):
    return create_agent(
        name="planning-agent",
        system_prompt=prompt,
        tools=tools,
        model=None,  # ❗ No custom model
        project_id=project_id,
        output_callback=output_callback
    )

# Same for coding_agent, testing_agent, review_agent
```

#### 2. BaseAgent Initialization (`src/agents/base_agent.py:54-59`)

When `model=None`, BaseAgent creates a model using Config values:

```python
if model is None:
    model = make_model(
        model=Config.LLM_MODEL,          # "gpt-4" from GUI
        temperature=Config.LLM_TEMPERATURE,  # 0.7 from GUI
        provider=Config.LLM_PROVIDER     # "openai" from GUI
    )
```

**Result**: All agents get the SAME model instance configuration.

---

## Is This Optimal?

### Current Approach: Same Model for All

**Pros:**
- ✅ Simple and predictable
- ✅ Consistent behavior across agents
- ✅ Easy to understand and debug
- ✅ Lower cognitive load for users
- ✅ Works well when using a single powerful model (e.g., GPT-4)

**Cons:**
- ❌ Can't optimize different agents for different tasks
- ❌ Can't use cheaper models for simple tasks
- ❌ Can't use specialized models (e.g., code-specific model for coding)
- ❌ One temperature for all tasks (not always optimal)

### Alternative: Task-Specific Models

**Example configuration:**
```python
Planning Agent  → gpt-4 (temp=0.3)     # Needs reasoning, moderate creativity
Coding Agent    → deepseek-coder (0.0) # Specialized for code, deterministic
Testing Agent   → gpt-3.5-turbo (0.0)  # Simpler task, faster/cheaper
Review Agent    → claude-3 (0.3)       # Good at analysis, moderate creativity
```

**Pros:**
- ✅ Cost optimization (use cheaper models for simpler tasks)
- ✅ Performance optimization (specialized models for specific tasks)
- ✅ Task-appropriate temperatures
- ✅ Flexibility and fine-tuning

**Cons:**
- ❌ More complex configuration
- ❌ Harder to debug (different models behave differently)
- ❌ Requires understanding which model is best for which task
- ❌ More API keys/setup needed

---

## Task-Specific Infrastructure EXISTS But Isn't Used!

### Available But Not Wired Up

The codebase has infrastructure for task-specific models that's **currently not being used**:

**File**: `src/core/llm/llm_providers.py:132-163`

```python
def get_model_for_task(task_type: str):
    """
    Get a model configured for a specific task type.
    Supports: 'coding', 'testing', 'planning', 'review', 'creative'
    """
    loader = get_model_config_loader()
    provider = LLMProviderConfig.PROVIDER

    # Get task-specific model from JSON config
    task_model = loader.get_task_model(provider, task_type)

    # Task-specific temperature settings
    task_temperatures = {
        'coding': 0.0,      # Deterministic for code generation
        'testing': 0.0,     # Deterministic for test generation
        'planning': 0.3,    # Slightly creative for planning
        'review': 0.3,      # Focused for code review
        'creative': 1.0,    # Maximum creativity
    }

    temperature = task_temperatures.get(task_type, Config.LLM_TEMPERATURE)

    return create_model(
        provider=provider,
        model=task_model,
        temperature=temperature
    )
```

This function exists but **agents never call it**!

---

## Recommendation: Keep Current Approach

### Why?

1. **Simplicity First**: For most users, one good model (e.g., GPT-4) works well for all tasks
2. **User Expectation**: When user selects a model in GUI, they expect ALL agents to use it
3. **Easier Debugging**: Same model = consistent behavior
4. **Cost-Effective for Most Users**: If using a free or cheap model, optimization doesn't matter

### When to Consider Task-Specific Models?

Only if:
- User is running MANY issues (cost becomes significant)
- User has access to specialized models (e.g., deepseek-coder)
- User wants to experiment with different models
- Performance optimization is critical

---

## How to Enable Task-Specific Models (Future Enhancement)

### Option 1: GUI Toggle (Simple)

Add a checkbox in GUI:
```
☐ Use task-specific models (Advanced)

If enabled:
- Planning: gpt-4 (reasoning)
- Coding: deepseek-coder (specialized)
- Testing: gpt-3.5-turbo (faster)
- Review: claude-3 (analysis)
```

### Option 2: Per-Agent Selection (Complex)

Allow users to select models for each agent:
```
Planning Agent:  [GPT-4        ▼] Temp: [0.3]
Coding Agent:    [DeepSeek Coder ▼] Temp: [0.0]
Testing Agent:   [GPT-3.5 Turbo  ▼] Temp: [0.0]
Review Agent:    [Claude-3       ▼] Temp: [0.3]
```

### Implementation (if needed)

**Minimal changes required:**

1. Modify `agent_factory.py`:
```python
def create_planning_agent(tools, project_id, pipeline_config, output_callback):
    # Use task-specific model if enabled
    model = get_model_for_task('planning') if use_task_models else None

    return create_agent(
        name="planning-agent",
        system_prompt=prompt,
        tools=tools,
        model=model,  # Task-specific model
        project_id=project_id,
        output_callback=output_callback
    )
```

2. Add GUI toggle to enable/disable task-specific models
3. Update JSON configs with task-specific model mappings

---

## Summary

### Current Behavior ✅
- **One model for all agents** (selected in GUI)
- Simple, predictable, works well for most users
- Infrastructure for task-specific models exists but isn't used

### When You Select "gpt-4" in GUI:
```
Planning Agent  → gpt-4 ✅
Coding Agent    → gpt-4 ✅
Testing Agent   → gpt-4 ✅
Review Agent    → gpt-4 ✅
All with same temperature (0.7) ✅
```

### Should This Change?
**NO, not for most users.**

The current approach is:
- ✅ User-friendly
- ✅ Predictable
- ✅ Sufficient for 90% of use cases
- ✅ Easy to understand and debug

Task-specific models can be added as an **optional advanced feature** later if users request it.

---

**Status**: Current behavior documented and confirmed as intentional design
**Date**: 2025-10-11
**Related**: `LLM_CONFIG_FIX.md` (GUI selection fix)
