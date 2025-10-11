# Architectural Planning & Implementation Strategy Analysis

## 🎯 **Core Question**

**Where and how do agents build project structure, and what architectural decisions should be made upfront in planning?**

---

## 📊 **Current State Analysis**

### **1. Who Creates What?**

| Component | Agent | Phase | Location |
|-----------|-------|-------|----------|
| **Planning Documents** | Planning Agent | PHASE 1 | `docs/ORCH_PLAN.json`, `docs/ARCHITECTURE.md` |
| **Source Code Structure** | Coding Agent | PHASE 3 (per issue) | `src/main/java/`, `src/`, etc. |
| **Dependency Files** | Coding Agent | PHASE 3 (Issue #1) | `pom.xml`, `requirements.txt`, `package.json` |
| **Test Structure** | Testing Agent | PHASE 3 (per issue) | `tests/`, `src/test/java/` |
| **Build Config** | System | Pre-existing | `.gitlab-ci.yml` (system-managed) |

**Code References:**
- Planning Agent: `planning_prompts.py:423-453` (creates ONLY docs/)
- Coding Agent: `coding_prompts.py:197-245` (creates src/ structure and files)
- Testing Agent: creates tests/ structure

---

### **2. Current ORCH_PLAN.json Structure**

**Location:** `planning_prompts.py:354-395`

```json
{
  "project_overview": "Brief description of project purpose and scope",
  "tech_stack": {
    "backend": "java|python|nodejs",
    "frontend": "none|react|vue|html-css-js",
    "database": "postgresql|mysql|mongodb|sqlite|none",
    "testing": "pytest|junit|jest"
  },
  "architecture_decision": {
    "structure_type": "Minimal|Standard|Enterprise",
    "reasoning": "Explanation of why this structure was chosen",
    "timestamp": "ISO 8601 timestamp",
    "alternatives_considered": ["List of other options evaluated"]
  },
  "implementation_order": [1, 2, 5, 3, 4, 6, 7, 8],
  "dependencies": {
    "2": [1],
    "3": [1]
  },
  "issues": [
    {
      "iid": 1,
      "title": "Issue title",
      "priority": "high|medium|low",
      "dependencies": [],
      "estimated_complexity": "low|medium|high"
    }
  ]
}
```

---

### **3. What's Currently Decided in Planning?**

**✅ Currently Decided:**
- Tech stack (backend, frontend, database, testing framework)
- Project structure type (Minimal/Standard/Enterprise)
- Implementation order (dependency-based)
- Issue priorities and dependencies
- Estimated complexity per issue

**❌ NOT Currently Decided:**
- **User Interface Type:** CLI vs GUI vs Web vs API-only
- **API Design:** REST vs GraphQL vs gRPC
- **Authentication Method:** JWT vs OAuth vs Session-based
- **Entry Points:** Main classes, CLI commands, API endpoints
- **Data Flow Patterns:** MVC vs MVVM vs Clean Architecture
- **Package/Module Structure:** Layered vs Feature-based vs Hexagonal
- **Configuration Strategy:** Environment variables vs config files
- **Error Handling Strategy:** Exceptions vs Result types
- **Logging Strategy:** Framework and verbosity level
- **Deployment Target:** Standalone app vs containerized vs serverless

---

## 🚨 **Critical Findings**

### **Finding 1: No Demo/Placeholder Code Policy**

**Search Result:**
```bash
grep -r "demo|placeholder|stub|TODO|FIXME" prompts/
# No matches found
```

**Analysis:**
✅ **GOOD!** There are NO instructions to create demo/placeholder/stub code.
✅ Agents are instructed to create **full, working implementations**.

**Code Evidence:**
- `coding_prompts.py:394-398`: "Implement ONE issue at a time" (not "create stub")
- `coding_prompts.py:484-489`: "ONLY signal completion when pipeline success" (must work)
- No use of TODO, FIXME, or placeholder patterns in prompts

**Conclusion:** The system is designed to create **production-ready code**, not prototypes.

---

### **Finding 2: Structure Creation Happens Late (Per-Issue)**

**Problem:**
- Planning Agent creates ONLY `docs/` directory
- Coding Agent creates `src/` structure **during Issue #1 implementation**
- No upfront project skeleton creation

**Current Flow:**
```
PHASE 1: Planning
  └─> Creates docs/ORCH_PLAN.json
  └─> NO src/ or package structure

PHASE 3: Issue #1 Implementation
  └─> Coding Agent creates src/main/java/com/example/
  └─> Coding Agent creates pom.xml or requirements.txt
  └─> First real structure appears HERE
```

**Risk:**
- If Issue #1 fails, no project structure exists
- Structure decisions made per-issue, not holistically
- No consistent package/module organization enforced

**Code Reference:** `coding_prompts.py:207-211`
```python
File Organization:
• Python: src/ for source, tests/ for tests
• Java: src/main/java/ for source, src/test/java/ for tests
```
→ This is just guidance, not enforced structure

---

### **Finding 3: Architectural Decisions Made Too Late**

**Current Process:**
1. Planning Agent analyzes issues
2. Decides "Standard" vs "Minimal" vs "Enterprise" structure
3. **But doesn't specify:**
   - What "Standard" means for THIS project
   - Which design patterns to use
   - How modules should be organized
   - How components should communicate

**Example Scenario:**

**Project:** Battleship Game (Java)

**Current Planning Output:**
```json
{
  "tech_stack": {"backend": "java", "testing": "junit"},
  "architecture_decision": {
    "structure_type": "Standard",
    "reasoning": "8 issues requiring team collaboration"
  }
}
```

**What Coding Agent Receives:**
- "Use Java"
- "Standard structure"
- ❌ **Does NOT know:**
  - Is this a CLI game with Scanner input?
  - Is this a GUI game with Swing/JavaFX?
  - Is this a REST API for a web client?
  - Should it use OOP with Game, Board, Ship classes?
  - Should it use functional style?
  - How should player input be handled?

**Result:**
- Coding Agent makes these decisions **ad-hoc** during Issue #1
- No consistency guarantee across issues
- No architectural coherence

---

## 💡 **Recommendations**

### **Recommendation 1: Enhanced ORCH_PLAN.json Structure**

Add comprehensive architectural decisions:

```json
{
  "project_overview": "Battleship console game for 2 players",
  "tech_stack": {
    "backend": "java",
    "frontend": "none",
    "database": "none",
    "testing": "junit"
  },

  // 🆕 NEW: User Interaction Architecture
  "user_interaction": {
    "type": "CLI",  // CLI | GUI | Web | REST_API | GraphQL_API | Hybrid
    "details": {
      "interface": "console",
      "input_method": "Scanner (System.in)",
      "output_method": "System.out.println",
      "error_display": "console messages"
    },
    "entry_points": [
      {
        "class": "com.example.battleship.Main",
        "method": "main",
        "purpose": "Application entry point"
      }
    ]
  },

  // 🆕 NEW: Architecture Patterns
  "architecture_patterns": {
    "primary_pattern": "Object-Oriented with MVC separation",
    "details": {
      "models": ["Game", "Board", "Ship", "Player", "Position"],
      "controllers": ["GameController", "InputController"],
      "views": ["ConsoleView"],
      "services": ["GameLogicService", "ValidationService"]
    },
    "design_principles": [
      "Single Responsibility Principle",
      "Dependency Injection for testability",
      "Interface-based design for flexibility"
    ]
  },

  // 🆕 NEW: Package Structure
  "package_structure": {
    "base_package": "com.example.battleship",
    "sub_packages": [
      {
        "name": "model",
        "purpose": "Domain entities (Game, Board, Ship, Player)",
        "example_classes": ["Game.java", "Board.java", "Ship.java"]
      },
      {
        "name": "controller",
        "purpose": "Game flow and input handling",
        "example_classes": ["GameController.java", "InputController.java"]
      },
      {
        "name": "view",
        "purpose": "Output formatting and display",
        "example_classes": ["ConsoleView.java"]
      },
      {
        "name": "service",
        "purpose": "Business logic and validation",
        "example_classes": ["GameLogicService.java", "ValidationService.java"]
      },
      {
        "name": "util",
        "purpose": "Utility classes",
        "example_classes": ["Constants.java", "Validator.java"]
      }
    ]
  },

  // 🆕 NEW: Data Flow
  "data_flow": {
    "pattern": "Layered Architecture",
    "flow": [
      "Main → GameController",
      "GameController → GameLogicService (business logic)",
      "GameController → ConsoleView (display)",
      "InputController → Validation → GameController"
    ],
    "state_management": "In-memory (Game object holds state)"
  },

  // 🆕 NEW: Error Handling Strategy
  "error_handling": {
    "strategy": "Exceptions with custom types",
    "exception_hierarchy": [
      "BattleshipException (base)",
      "InvalidMoveException",
      "InvalidInputException",
      "GameStateException"
    ],
    "user_feedback": "Catch at controller level, display friendly messages via ConsoleView"
  },

  // 🆕 NEW: Configuration Strategy
  "configuration": {
    "type": "Constants class",
    "location": "com.example.battleship.util.Constants",
    "examples": [
      "BOARD_SIZE = 10",
      "SHIP_TYPES and SHIP_LENGTHS",
      "MAX_TURNS (if applicable)"
    ]
  },

  // 🆕 NEW: Testing Strategy
  "testing_strategy": {
    "framework": "JUnit 5",
    "patterns": [
      "Unit tests for each model class",
      "Integration tests for GameController",
      "Test doubles (mocks) for input/output"
    ],
    "coverage_target": "80% minimum",
    "test_organization": "Mirror src structure in src/test/java"
  },

  // Existing fields
  "architecture_decision": {
    "structure_type": "Standard",
    "reasoning": "OOP with clear separation of concerns for maintainability"
  },
  "implementation_order": [1, 2, 3, 4, 5],
  "dependencies": {...},
  "issues": [...]
}
```

---

### **Recommendation 2: Create Skeleton Structure in Planning Phase**

**Current:** Planning Agent creates ONLY `docs/ORCH_PLAN.json`

**Proposed:** Planning Agent creates:

```
docs/
  ├── ORCH_PLAN.json (enhanced with architectural decisions)
  ├── ARCHITECTURE.md (detailed architecture documentation)
  ├── API_DESIGN.md (if API project: endpoint specs, request/response formats)
  └── USER_GUIDE_TEMPLATE.md (if CLI/GUI: how users will interact)
```

**For Projects with Clear Structure Needs:**

Planning Agent could OPTIONALLY create package skeleton:

```
src/main/java/com/example/battleship/
  ├── model/
  ├── controller/
  ├── view/
  ├── service/
  └── util/
```

**With placeholder .gitkeep files ONLY (not code).**

**Rationale:**
- Ensures consistent package structure from start
- Coding Agent knows exactly where to place files
- No structural decisions made ad-hoc

**Concern:**
- Violates current "Planning Agent creates only docs" rule
- Could be seen as implementation, not planning

**Alternative:**
- Keep current approach (Coding Agent creates structure)
- But **require** Coding Agent to follow `package_structure` from ORCH_PLAN.json exactly

---

### **Recommendation 3: Planning Agent Analysis Enhancements**

**Add to Planning Agent Workflow (PHASE 2: Dependency Analysis):**

```python
PHASE 2.5: ARCHITECTURAL ANALYSIS

Based on issues, determine:

1. User Interaction Type:
   - Look for keywords: "CLI", "command line", "console" → CLI
   - Look for keywords: "GUI", "window", "interface" → GUI
   - Look for keywords: "API", "endpoint", "REST", "GraphQL" → API
   - Look for keywords: "web", "browser", "HTML" → Web Application

2. Core Entities (from issue descriptions):
   - Extract nouns: "Game", "Board", "Ship", "Player"
   - These become model classes

3. User Actions (from issue descriptions):
   - Extract verbs: "place ship", "fire shot", "check win"
   - These become controller methods or API endpoints

4. Data Flow:
   - Analyze issue dependencies to understand data flow
   - Example: "Place ship" requires "Board exists" → Board created first

5. Configuration Needs:
   - Look for configurable values: board size, ship types, etc.
   - Document in configuration strategy

6. Error Scenarios:
   - Extract from acceptance criteria: "invalid input", "out of bounds"
   - Define error handling strategy

Output: Enhanced ORCH_PLAN.json with all architectural decisions
```

---

### **Recommendation 4: Coding Agent Enforcement**

**Update Coding Agent Prompts:**

```python
PHASE 1: CONTEXT GATHERING

Step 3 - Architecture Compliance:
• Read docs/ORCH_PLAN.json
• Extract user_interaction, architecture_patterns, package_structure
• STRICTLY FOLLOW the defined architecture:
  ❌ NEVER create different package structure
  ❌ NEVER use different design patterns
  ❌ NEVER ignore user_interaction specifications
  ✅ ALWAYS place files in correct packages per ORCH_PLAN.json
  ✅ ALWAYS use specified patterns and principles
  ✅ ALWAYS implement according to architectural decisions

Step 4 - Entry Point Verification (Issue #1 only):
• If issue is #1 (first implementation):
  • Create Main.java (or main.py) as specified in entry_points
  • Implement basic skeleton: initialize app, call controller
  • Create package structure per package_structure

Step 5 - Package Placement Verification:
• Before creating any class:
  • Check ORCH_PLAN.json for correct package
  • Example: "Game.java" → "model" package → "com.example.battleship.model.Game"
  • Example: "GameController.java" → "controller" package
```

---

### **Recommendation 5: Documentation Generation**

**Planning Agent should create:**

1. **`docs/ARCHITECTURE.md`** (REQUIRED):
```markdown
# Architecture Documentation

## User Interaction
- **Type:** CLI (Console application)
- **Entry Point:** `com.example.battleship.Main.main()`
- **Input:** Scanner reading from System.in
- **Output:** System.out.println()

## Package Structure
```
com.example.battleship/
  ├── model/        # Domain entities (Game, Board, Ship, Player)
  ├── controller/   # Game flow and input handling
  ├── view/         # Output formatting
  ├── service/      # Business logic
  └── util/         # Utilities and constants
```

## Design Patterns
- **Primary:** Object-Oriented with MVC separation
- **Principles:** SRP, Dependency Injection, Interface-based design

## Data Flow
Main → GameController → GameLogicService → Models
           ↓
      ConsoleView (display)

## Error Handling
- Custom exceptions: BattleshipException hierarchy
- User-friendly error messages via ConsoleView
```

2. **`docs/API_DESIGN.md`** (if API project):
```markdown
# API Design Specification

## Endpoints

### POST /api/game/start
**Request:**
```json
{
  "player1": "Alice",
  "player2": "Bob"
}
```

**Response:**
```json
{
  "gameId": "uuid",
  "status": "setup",
  "currentPlayer": "Alice"
}
```
```

3. **`docs/USER_GUIDE.md`** (if CLI/GUI):
```markdown
# User Guide

## Starting the Game
```bash
java -jar battleship.jar
```

## Commands
- `place <ship> <x> <y> <direction>` - Place a ship
- `fire <x> <y>` - Fire at position
- `quit` - Exit game

## Example Session
```
> place carrier 0 0 horizontal
Ship placed successfully!
> fire 5 5
Miss!
```
```

---

## ✅ **Proposed Enhanced Planning Workflow**

```
PHASE 1: Issue Analysis
  └─> Extract requirements, dependencies, entities, actions

PHASE 2: Architectural Analysis 🆕
  └─> Determine user interaction type (CLI/GUI/API)
  └─> Identify core entities (models)
  └─> Define package structure
  └─> Choose design patterns
  └─> Define error handling strategy
  └─> Define configuration approach
  └─> Define data flow

PHASE 3: Create Enhanced ORCH_PLAN.json 🆕
  └─> Include all architectural decisions
  └─> Document user_interaction, architecture_patterns, package_structure
  └─> Document error_handling, configuration, testing_strategy

PHASE 4: Create Documentation 🆕
  └─> docs/ARCHITECTURE.md (detailed architecture)
  └─> docs/API_DESIGN.md (if API project)
  └─> docs/USER_GUIDE_TEMPLATE.md (if CLI/GUI)

PHASE 5: Create Planning Report
  └─> Signal PLANNING_PHASE_COMPLETE
```

---

## 📋 **Implementation Checklist**

To achieve full architectural planning:

- [ ] Extend `ORCH_PLAN.json` schema with new fields:
  - [ ] `user_interaction`
  - [ ] `architecture_patterns`
  - [ ] `package_structure`
  - [ ] `data_flow`
  - [ ] `error_handling`
  - [ ] `configuration`
  - [ ] `testing_strategy`

- [ ] Update Planning Agent prompt:
  - [ ] Add PHASE 2.5: Architectural Analysis
  - [ ] Add instructions for determining UI type
  - [ ] Add instructions for extracting entities/actions from issues
  - [ ] Add documentation generation (ARCHITECTURE.md, etc.)

- [ ] Update Coding Agent prompt:
  - [ ] Add architecture compliance check
  - [ ] Enforce package structure from ORCH_PLAN.json
  - [ ] Enforce design patterns from ORCH_PLAN.json
  - [ ] Add entry point creation for Issue #1

- [ ] Update Testing Agent prompt:
  - [ ] Read testing_strategy from ORCH_PLAN.json
  - [ ] Follow test organization rules

- [ ] Documentation:
  - [ ] Create ORCH_PLAN.json schema documentation
  - [ ] Create examples for different project types (CLI, GUI, API)
  - [ ] Update orchestration flow diagrams

---

## 🎯 **Key Principles**

1. **Plan Everything Upfront**
   - All architectural decisions made in Planning Phase
   - Coding Agent is an **executor**, not an architect

2. **No Demo/Placeholder Code**
   - All code must be production-ready
   - No TODOs, FIXMEs, or stubs
   - Verified by pipeline success

3. **Consistency Through Planning**
   - ORCH_PLAN.json is the **single source of truth**
   - All agents follow the plan exactly
   - No ad-hoc architectural decisions

4. **Complete Documentation**
   - Architecture decisions are documented
   - User guides explain how to interact
   - API specs define contracts

5. **Working Software from Day 1**
   - Issue #1 should produce a minimal but **runnable** application
   - Each subsequent issue adds features to working base
   - Every merge to master leaves software in working state

---

## 📚 **Summary**

**Current State:**
- ✅ No demo/placeholder code (GOOD!)
- ✅ Tech stack decided in planning
- ❌ No user interaction type planning (CLI vs GUI)
- ❌ No package structure planning
- ❌ No design pattern specification
- ❌ Structure created ad-hoc during Issue #1

**Proposed State:**
- ✅ Complete architectural planning upfront
- ✅ Enhanced ORCH_PLAN.json with all decisions
- ✅ Documentation generation (ARCHITECTURE.md, USER_GUIDE.md, API_DESIGN.md)
- ✅ Coding Agent follows plan exactly
- ✅ Consistent, production-ready code from start

**Result:** Fully working software at the end, with clear architecture and no guesswork.
