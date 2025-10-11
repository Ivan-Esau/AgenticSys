# LLM Configuration Fix - GUI Selection Issue

## Problem Summary

The LLM provider and model selections made in the Web GUI were being **completely ignored**. The system always used the values from the `.env` file instead of the user's GUI selections.

## Root Cause

Three interconnected issues:

1. **Data Structure Mismatch**
   - Frontend sent: `config['llm_config'] = {provider, model, temperature}` (nested object)
   - Backend expected: `config['llm_provider']`, `config['llm_model']`, etc. (flat structure)
   - Result: Backend extracted `'unknown'` for all values

2. **Config Not Used for LLM Initialization**
   - The extracted config was only passed to `RunLogger` for analytics
   - NOT passed to agents for actual LLM initialization
   - Agents always used `Config` class which reads from environment variables

3. **Static Environment Loading**
   - `Config` class loaded environment variables at startup
   - No mechanism to override with runtime/GUI selections
   - User selections had no way to reach the agents

## The Fix

### Location
`web_gui/backend/core/orchestrator.py` lines 141-195

### Changes Made

#### 1. Correct Extraction from Nested Structure
```python
# BEFORE (broken)
llm_config = {
    'provider': config.get('llm_provider', 'unknown'),  # ❌ NOT FOUND
    'model': config.get('llm_model', 'unknown'),        # ❌ NOT FOUND
    'temperature': config.get('llm_temperature', 0.0)   # ❌ NOT FOUND
}

# AFTER (fixed)
llm_config_from_gui = config.get('llm_config', {})
llm_provider = llm_config_from_gui.get('provider', os.getenv('LLM_PROVIDER', 'deepseek'))
llm_model = llm_config_from_gui.get('model', os.getenv('LLM_MODEL', 'deepseek-chat'))
llm_temperature = llm_config_from_gui.get('temperature', float(os.getenv('LLM_TEMPERATURE', '0.7')))
```

#### 2. Dynamic Environment Variable Update
```python
# Update environment BEFORE supervisor initialization
if llm_provider:
    os.environ['LLM_PROVIDER'] = str(llm_provider)
if llm_model:
    os.environ['LLM_MODEL'] = str(llm_model)
if llm_temperature is not None:
    os.environ['LLM_TEMPERATURE'] = str(llm_temperature)

# Force reload Config to pick up new values
import importlib
import src.core.llm.config
importlib.reload(src.core.llm.config)
```

#### 3. Added Debug Logging
```python
print(f"[LLM CONFIG] GUI selections:")
print(f"  Provider: {llm_provider}")
print(f"  Model: {llm_model}")
print(f"  Temperature: {llm_temperature}")
print(f"[LLM CONFIG] Config reloaded - agents will now use GUI selections")
```

## How It Works Now

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER SELECTS IN GUI                                          │
│    - Provider: openai                                           │
│    - Model: gpt-4                                               │
│    - Temperature: 0.7                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FRONTEND (ui.js:579)                                         │
│    Sends: {                                                     │
│      llm_config: {                                              │
│        provider: "openai",                                      │
│        model: "gpt-4",                                          │
│        temperature: 0.7                                         │
│      }                                                          │
│    }                                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. ORCHESTRATOR (orchestrator.py:146) ✅ FIXED                 │
│    - Extracts from nested structure                            │
│    - Updates environment variables:                            │
│      os.environ['LLM_PROVIDER'] = 'openai'                      │
│      os.environ['LLM_MODEL'] = 'gpt-4'                          │
│      os.environ['LLM_TEMPERATURE'] = '0.7'                      │
│    - Reloads Config class                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. CONFIG CLASS (config.py:35)                                 │
│    Now reads updated environment:                              │
│    - LLM_PROVIDER = 'openai' ✅                                 │
│    - LLM_MODEL = 'gpt-4' ✅                                     │
│    - LLM_TEMPERATURE = 0.7 ✅                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. AGENTS (base_agent.py:54)                                   │
│    Create LLM using GUI selections:                            │
│    model = make_model(                                         │
│      provider=Config.LLM_PROVIDER,  # 'openai' from GUI ✅      │
│      model=Config.LLM_MODEL,        # 'gpt-4' from GUI ✅       │
│      temperature=Config.LLM_TEMPERATURE  # 0.7 from GUI ✅      │
│    )                                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Testing

### Test Files Created

1. **`test_llm_config_flow.py`**
   - Demonstrates the bug (before fix)
   - Shows the solution (after fix)
   - Proves GUI selections now work

2. **`test_llm_fix_integration.py`**
   - End-to-end integration test
   - Tests extraction → environment update → Config reload
   - Tests fallback to .env when GUI config is empty

### Run Tests
```bash
python test_llm_config_flow.py
python test_llm_fix_integration.py
```

### Expected Output
```
[SUCCESS] Integration test PASSED!
GUI selections are now correctly applied to agents.

[SUCCESS] Fallback test PASSED!
System correctly falls back to .env when GUI config is missing.

ALL TESTS PASSED!
```

## Benefits

1. ✅ **User Control**: GUI selections now actually control which LLM is used
2. ✅ **Proper Fallback**: Falls back to .env when GUI doesn't provide config
3. ✅ **Debug Visibility**: Console logs show exactly what LLM config is being used
4. ✅ **Analytics Fixed**: RunLogger now receives correct provider/model values
5. ✅ **No Breaking Changes**: Backward compatible with existing .env configuration

## Verification in Production

When system runs, you'll see console output:
```
[LLM CONFIG] GUI selections:
  Provider: openai
  Model: gpt-4
  Temperature: 0.7
[LLM CONFIG] Set LLM_PROVIDER=openai
[LLM CONFIG] Set LLM_MODEL=gpt-4
[LLM CONFIG] Set LLM_TEMPERATURE=0.7
[LLM CONFIG] Config reloaded - agents will now use GUI selections
```

## Future Improvements

While this fix works, a cleaner approach would be:

1. **RuntimeConfig Class**: Create a config class that can be passed down explicitly
2. **Dependency Injection**: Pass config to Supervisor → Executor → Agents
3. **Avoid Global State**: Remove reliance on environment variables for runtime config

These improvements are tracked in separate issues but not required for current functionality.

---

**Status**: ✅ FIXED and TESTED
**Date**: 2025-10-11
**Files Modified**:
- `web_gui/backend/core/orchestrator.py` (lines 141-195)

**Test Files Created**:
- `test_llm_config_flow.py`
- `test_llm_fix_integration.py`
