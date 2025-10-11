# LLM Config Debug Logging - What You Should See

## Date: 2025-10-11

## Overview

Enhanced debug logging to verify that GUI LLM selections are actually being used by agents at runtime.

---

## What Was Added

### 1. Orchestrator Banner (orchestrator.py:153-183)

When the system starts, you'll see a prominent banner showing:
- What was selected in the GUI
- Environment variables being updated
- Config class reload confirmation

### 2. Agent Initialization Logging (base_agent.py:60-64)

When each agent is created, it will print:
- The actual provider, model, and temperature from Config
- This confirms agents are using the updated values

---

## Example Output - Testing the Fix

### Scenario: Select OpenAI GPT-4 with temp 0.7 in GUI

**Step 1: GUI sends config to backend**
```
Frontend sends:
{
  "project_id": "123",
  "llm_config": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7
  }
}
```

**Step 2: Orchestrator extracts and applies (you should see this in console):**
```
======================================================================
[LLM CONFIG] Applying GUI selections:
======================================================================
  Provider: openai
  Model: gpt-4
  Temperature: 0.7
======================================================================

[LLM CONFIG] Set LLM_PROVIDER=openai
[LLM CONFIG] Set LLM_MODEL=gpt-4
[LLM CONFIG] Set LLM_TEMPERATURE=0.7

[LLM CONFIG] Config reloaded - agents will use GUI selections
```

**Step 3: Each agent initialization (you should see this when agents are created):**
```
[PLANNING-AGENT] LLM Config:
  Provider: openai
  Model: gpt-4
  Temperature: 0.7

[CODING-AGENT] LLM Config:
  Provider: openai
  Model: gpt-4
  Temperature: 0.7

[TESTING-AGENT] LLM Config:
  Provider: openai
  Model: gpt-4
  Temperature: 0.7

[REVIEW-AGENT] LLM Config:
  Provider: openai
  Model: gpt-4
  Temperature: 0.7
```

---

## What This Proves

### ✅ If You See Matching Values:
- **Orchestrator shows**: `Provider: openai, Model: gpt-4, Temperature: 0.7`
- **Agents show**: `Provider: openai, Model: gpt-4, Temperature: 0.7`
- **Result**: GUI selections are working! ✅

### ❌ If Values Don't Match:
- **Orchestrator shows**: `Provider: openai, Model: gpt-4, Temperature: 0.7`
- **Agents show**: `Provider: deepseek, Model: deepseek-chat, Temperature: 0.0`
- **Result**: Config reload failed (shouldn't happen with our fix)

---

## Testing Steps

1. **Start the web GUI server**
   ```bash
   python -m uvicorn web_gui.backend.app:app --host 0.0.0.0 --port 8000
   ```

2. **Open browser to http://localhost:8000**

3. **Select different provider/model in GUI**
   - For example: OpenAI / GPT-4 / Temperature 0.7

4. **Click "Start" button**

5. **Watch the console output**
   - You should see the banner with GUI selections
   - Then see each agent print its actual config
   - Values should MATCH your GUI selections

---

## Previous Behavior (Before Fix)

### What You Would See (WRONG):
```
[DEBUG] Current LLM config: provider=deepseek, model=deepseek-chat, temp=0.0

[PLANNING-AGENT] LLM Config:
  Provider: deepseek
  Model: deepseek-chat
  Temperature: 0.0
```

Even if you selected OpenAI GPT-4 in GUI, it would use deepseek!

---

## New Behavior (After Fix)

### What You Should See (CORRECT):
```
======================================================================
[LLM CONFIG] Applying GUI selections:
======================================================================
  Provider: openai
  Model: gpt-4
  Temperature: 0.7
======================================================================

[LLM CONFIG] Set LLM_PROVIDER=openai
[LLM CONFIG] Set LLM_MODEL=gpt-4
[LLM CONFIG] Set LLM_TEMPERATURE=0.7

[LLM CONFIG] Config reloaded - agents will use GUI selections

[PLANNING-AGENT] LLM Config:
  Provider: openai
  Model: gpt-4
  Temperature: 0.7
```

GUI selections are actually used! ✅

---

## Why This Matters

Without this debug logging, it was unclear if the fix was working. Now:
1. **Transparency**: You can see exactly what's happening
2. **Verification**: You can verify GUI selections are applied
3. **Debugging**: If something's wrong, you'll see exactly where

---

## Code Changes

### Files Modified:

1. **web_gui/backend/core/orchestrator.py** (lines 153-183)
   - Added prominent banner showing GUI selections
   - Added confirmation after each environment variable update
   - Added confirmation after Config reload

2. **src/agents/base_agent.py** (lines 60-64)
   - Added debug output showing actual Config values
   - Printed when agent is initialized (before model creation)
   - Shows provider, model, and temperature from Config class

---

## Related Documentation

- `LLM_CONFIG_FIX.md` - Original fix for GUI selections being ignored
- `TEMPERATURE_FIX_TESTING.md` - Temperature testing documentation
- `SINGLE_MODEL_VS_TASK_SPECIFIC.md` - Explanation of model usage

---

## Testing Checklist

Test these scenarios and verify output matches:

- [ ] Select DeepSeek / deepseek-chat / 0.0
  - Orchestrator banner shows: deepseek, deepseek-chat, 0.0
  - Agents show: deepseek, deepseek-chat, 0.0

- [ ] Select OpenAI / gpt-4 / 0.7
  - Orchestrator banner shows: openai, gpt-4, 0.7
  - Agents show: openai, gpt-4, 0.7

- [ ] Select Ollama / llama3.2 / 1.0
  - Orchestrator banner shows: ollama, llama3.2, 1.0
  - Agents show: ollama, llama3.2, 1.0

- [ ] Change temperature mid-session (restart system)
  - New temperature should appear in both orchestrator and agents

---

## Conclusion

With these debug logs, you can now **visually confirm** that your GUI selections are being applied. The prominent banners and agent initialization logs make it impossible to miss what configuration is actually being used.

**Status**: Debug logging enhanced ✅
**Ready for testing**: YES ✅

---

**Next Steps**: Start the system, select a provider/model in GUI, and watch the console output to verify it's working!
