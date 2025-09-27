# Orchestrator Module Structure

## Overview
The orchestrator module has been refactored from a monolithic 1168-line file into a clean, modular architecture with clear separation of concerns.

## Directory Structure

```
src/orchestrator/
├── __init__.py              # Main module exports
├── supervisor.py            # Main orchestrator (refactored, ~400 lines)
│
├── core/                    # Core execution components
│   ├── __init__.py
│   ├── router.py           # Task routing logic
│   ├── performance.py      # Performance tracking
│   └── agent_executor.py   # Agent execution coordination
│
├── managers/               # Business logic managers
│   ├── __init__.py
│   ├── issue_manager.py    # GitLab issue management
│   ├── pipeline_manager.py # CI/CD pipeline operations
│   └── planning_manager.py # Planning and prioritization
│
├── pipeline/              # Pipeline-specific components
│   ├── __init__.py
│   ├── pipeline_config.py  # Pipeline configuration
│   └── pipeline_monitor.py # Pipeline monitoring utilities
│
├── integrations/          # External service integrations
│   ├── __init__.py
│   └── mcp_integration.py  # MCP server integration
│
├── utils/                 # Utility modules
│   ├── __init__.py
│   └── completion_markers.py # Agent completion detection
│
└── legacy/               # Preserved original code
    ├── __init__.py
    ├── supervisor_original.py      # Initial backup
    └── supervisor_old_monolithic.py # Monolithic version
```

## Module Responsibilities

### Core Components (`core/`)
- **router.py**: Routes tasks to appropriate agents
- **performance.py**: Tracks execution metrics and timing
- **agent_executor.py**: Manages agent execution flow

### Managers (`managers/`)
- **issue_manager.py**:
  - Issue validation and tracking
  - Completion detection
  - Feature branch creation
  - Issue prioritization

- **pipeline_manager.py**:
  - Pipeline configuration
  - Tech stack detection
  - Pipeline monitoring
  - Failure analysis

- **planning_manager.py**:
  - Planning execution with retry
  - Issue prioritization
  - Dependency analysis
  - Plan parsing

### Pipeline Components (`pipeline/`)
- **pipeline_config.py**: Dynamic pipeline YAML generation
- **pipeline_monitor.py**: Active pipeline waiting and monitoring

### Integrations (`integrations/`)
- **mcp_integration.py**: MCP server and tool management

### Utilities (`utils/`)
- **completion_markers.py**: Success/failure pattern detection

## Benefits of New Structure

1. **Maintainability**: Each module has a single, clear responsibility
2. **Testability**: Components can be tested in isolation
3. **Scalability**: Easy to add new managers or integrations
4. **Readability**: Reduced file sizes (max ~400 lines vs 1168)
5. **Reusability**: Modules can be imported independently

## Usage

```python
# Import the main supervisor
from src.orchestrator import Supervisor, run_supervisor

# Or import specific components
from src.orchestrator.managers import IssueManager
from src.orchestrator.pipeline import PipelineConfig
from src.orchestrator.core import Router
```

## Migration from Old Structure

The original monolithic supervisor is preserved in `legacy/` for reference.
All functionality has been maintained while improving the architecture.

## Development Guidelines

1. Keep modules focused on their specific domain
2. Use dependency injection rather than tight coupling
3. Maintain clear interfaces between modules
4. Document public APIs in module docstrings
5. Keep individual files under 500 lines