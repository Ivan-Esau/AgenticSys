# Architectural Planning Update - Simple Enhancement

## 🎯 **What Changed**

Enhanced Planning Agent to make architectural decisions upfront, and Coding Agent to follow them.

---

## ✅ **Changes Made**

### **1. Planning Agent - Enhanced ORCH_PLAN.json**

**File:** `src/agents/prompts/planning_prompts.py`

**Added 4 New Fields to ORCH_PLAN.json:**

```json
{
  "user_interface": {
    "type": "CLI|GUI|Web|REST_API|none",
    "entry_point": "Main class/file that starts the application",
    "description": "How users interact with the software"
  },
  "package_structure": {
    "style": "layered|feature-based|simple",
    "packages": ["model", "controller", "service", "util"]
  },
  "core_entities": ["Game", "Board", "Ship", "Player"],
  "architecture_decision": {
    "patterns": ["MVC|Layered|Clean|Simple"]  // Added to existing field
  }
}
```

**Added PHASE 3: Architectural Analysis**

Simple rules to determine these values:

1. **User Interface Type** - Look for keywords in issues:
   - "command line", "console", "CLI" → CLI
   - "GUI", "window", "Swing" → GUI
   - "web", "browser" → Web
   - "API", "endpoint", "REST" → REST_API

2. **Core Entities** - Extract nouns from issue titles:
   - "Create Game board" → "Board"
   - "Implement Ship placement" → "Ship"

3. **Package Structure** - Based on project size:
   - <5 issues → simple
   - 5-15 issues → layered (model, service, util)
   - 15+ issues → layered (model, controller, service, view, util)

4. **Entry Point** - Based on tech stack:
   - Java → "com.example.project.Main"
   - Python → "src/main.py"
   - JavaScript → "src/index.js"

---

### **2. Coding Agent - Follow Architecture**

**File:** `src/agents/prompts/coding_prompts.py`

**Added Step 2: Architecture Analysis (in PHASE 1)**

```
Read ORCH_PLAN.json and extract:
• user_interface.type → Know if CLI/GUI/API
• user_interface.entry_point → Main class/file location
• package_structure.packages → Where to place files
• core_entities → Main classes to implement
• architecture_decision.patterns → Design patterns to use

🚨 CRITICAL: FOLLOW ARCHITECTURE EXACTLY
✅ Place files in packages specified
✅ Use interface type specified
❌ NEVER create different package structure
```

**Updated PHASE 2: Implementation Design**

Added file placement rules:
```
File Placement (from ORCH_PLAN.json):
• Check package_structure.packages for correct location
• Example: "Board" entity → "model" package
• Example: "GameController" → "controller" package

Entry Point Creation (Issue #1 ONLY):
• Create entry point as specified in user_interface.entry_point
• Java: Main.java with main() method
• Python: main.py with if __name__ == "__main__"
```

**Updated Required Actions**

Added architecture compliance:
```
✅ REQUIRED ACTIONS:
• ALWAYS read ORCH_PLAN.json and follow architectural decisions
• ALWAYS place files in packages specified in package_structure
• ALWAYS create entry point as specified (for issue #1)
• ALWAYS use interface type from user_interface.type
```

---

## 📊 **Example: Before vs After**

### **Battleship Game Example**

**BEFORE (Old ORCH_PLAN.json):**
```json
{
  "tech_stack": {"backend": "java"},
  "architecture_decision": {
    "structure_type": "Standard"
  }
}
```
→ Coding Agent doesn't know: CLI or GUI? What packages? Where to put files?

**AFTER (New ORCH_PLAN.json):**
```json
{
  "tech_stack": {"backend": "java"},
  "user_interface": {
    "type": "CLI",
    "entry_point": "com.example.battleship.Main",
    "description": "Console game using Scanner for input"
  },
  "package_structure": {
    "style": "layered",
    "packages": ["model", "controller", "service", "util"]
  },
  "core_entities": ["Game", "Board", "Ship", "Player"],
  "architecture_decision": {
    "structure_type": "Standard",
    "patterns": ["MVC"]
  }
}
```
→ Coding Agent knows: CLI game, Main entry point, use model/controller/service packages, create Game/Board/Ship/Player classes

**Result:**
- ✅ Clear architecture from day 1
- ✅ Consistent file placement
- ✅ No ad-hoc decisions
- ✅ All agents follow the same plan

---

## 🎯 **How It Works**

### **Planning Phase:**

1. Planning Agent analyzes all issues
2. Looks for keywords to determine UI type (CLI/GUI/API)
3. Extracts entities from issue titles (Game, Board, Ship)
4. Determines package structure based on project size
5. Creates enhanced ORCH_PLAN.json with all decisions
6. Merges planning-structure branch to master

### **Implementation Phase (per issue):**

1. Coding Agent reads ORCH_PLAN.json from work_branch
2. Extracts user_interface, package_structure, core_entities
3. Places files in correct packages:
   - Board.java → model package
   - GameController.java → controller package
4. For Issue #1: Creates entry point (Main.java) as specified
5. Uses UI type (CLI/GUI/API) to guide implementation
6. Creates fully working code following the architecture

---

## ✅ **Benefits**

1. **Consistency:** All files in correct locations
2. **Clarity:** Everyone knows the architecture upfront
3. **No Guesswork:** Coding Agent follows predefined plan
4. **Working Software:** Clear entry points from Issue #1
5. **Simple:** Minimal changes to existing prompts

---

## 📝 **Files Modified**

1. `src/agents/prompts/planning_prompts.py`
   - Added PHASE 3: Architectural Analysis
   - Enhanced ORCH_PLAN.json schema with 4 new fields

2. `src/agents/prompts/coding_prompts.py`
   - Added Step 2: Architecture Analysis in PHASE 1
   - Updated PHASE 2: File placement rules
   - Added architecture compliance to required actions

**Both files compile successfully** ✅

---

## 🚀 **Next Steps**

The system will now:

1. **Planning Phase:** Create enhanced ORCH_PLAN.json with:
   - User interface type (CLI/GUI/Web/API)
   - Package structure
   - Core entities
   - Entry point
   - Design patterns

2. **Implementation Phase:** Coding Agent will:
   - Read architectural decisions
   - Place files in correct packages
   - Create entry point for Issue #1
   - Follow the architecture consistently

**Result:** Fully working software with clear, consistent architecture from day 1.
