# Project Structure

Clean architecture for the GitLab Agent Orchestrator.

## Core Structure

```
├── docker-compose.yml          # MCP server configuration
├── requirements.txt            # Python dependencies  
├── run.py                     # Main entry point
├── docs/                      # Documentation
│   ├── PROJECT_STRUCTURE.md   # This file
│   └── CONTEXT_ENGINEERING_PLAN.md  # Context optimization research
└── src/                       # Source code
    ├── agents/                # Agent implementations
    │   ├── base_agent.py      # Base agent with state management
    │   ├── planning_agent.py  # Project planning
    │   ├── coding_agent.py    # Feature implementation  
    │   ├── testing_agent.py   # Test creation
    │   ├── review_agent.py    # Code review & merge
    │   └── pipeline_agent.py  # CI/CD monitoring
    ├── core/                  # Core utilities
    │   ├── config.py          # Configuration management
    │   ├── constants.py       # System constants
    │   ├── llm_config.py      # LLM model configuration
    │   ├── state.py           # Shared state management
    │   └── utils.py           # Utility functions
    ├── infrastructure/        # External integrations
    │   └── mcp_client.py      # MCP client management
    └── orchestrator/          # Agent coordination
        └── supervisor.py      # Main orchestrator
```

## Architecture Principles

### 1. Single MCP Client Management
- **Supervisor** creates and manages ONE MCP client
- **Agents** receive tools as parameters (stateless)
- No more "Session termination failed: 404" errors

### 2. Shared State Management  
- **ProjectState** provides shared memory between agents
- File caching to prevent redundant API calls
- Agent coordination and handoff data

### 3. Clean Separation of Concerns
- **Agents**: Specialized task execution (planning, coding, testing, review)
- **Supervisor**: Orchestration and workflow management  
- **Infrastructure**: External service connections (MCP, GitLab)
- **Core**: Shared utilities and configuration

### 4. Context Engineering Ready
- Agents designed to receive focused context
- State management supports intelligent caching
- Foundation for contextual intelligence improvements

## Usage

```python
from src.orchestrator.supervisor import Supervisor

# Create and initialize supervisor  
supervisor = Supervisor('project_id')
await supervisor.initialize()

# Run orchestrated workflow
await supervisor.orchestrate_full_implementation()

# Cleanup
await supervisor.cleanup()
```

## Key Features

✅ **Centralized MCP Management**: One client, managed by supervisor  
✅ **Shared State**: Agents share context and prevent redundant work  
✅ **Agent Specialization**: Each agent has focused responsibilities  
✅ **Error Handling**: Robust error handling and recovery  
✅ **Clean Architecture**: Clear separation of concerns  
✅ **Context Engineering**: Foundation for intelligent context selection  

## Removed Components

- Test files (`test_*.py`) - were experimental/demo only
- Experimental agents (`planning_agent_smart.py`) - proof of concept
- Context engine (`context_engine.py`) - research prototype  
- Cache files (`__pycache__/`) - temporary build artifacts

The system is now clean, focused, and ready for production use.