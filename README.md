# GitLab Agent System

A sophisticated multi-agent system that automates GitLab project implementation using LangChain, LangGraph, and DeepSeek AI.

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Edit `.env` file with your GitLab and DeepSeek credentials

3. **Start MCP server:**
   ```bash
   docker-compose up -d
   ```

4. **Run the system:**
   ```bash
   # Analyze project (no changes)
   python run.py --project-id 114
   
   # Full implementation
   python run.py --project-id 114 --apply
   
   # Single issue
   python run.py --project-id 114 --issue 1 --apply
   ```

## Architecture

```
├── run.py              # Main entry point
├── requirements.txt    # Dependencies
├── docker-compose.yml  # MCP server configuration
├── .env               # Configuration
└── src/
    ├── core/          # Core system (config, state, utils)
    ├── agents/        # Specialized agents (planning, coding, testing, review, pipeline)
    ├── orchestrator/  # Supervisor pattern orchestrator
    └── infrastructure/ # MCP client for GitLab tools
```

## Key Features

- **Supervisor Pattern**: Central orchestrator coordinates specialized agents
- **Shared State Management**: Intelligent caching and coordination between agents
- **Single MCP Client**: Efficient GitLab API integration
- **LangGraph Integration**: ReAct pattern for autonomous reasoning
- **DeepSeek AI**: Task-specific model selection for optimal performance

## System Flow

1. **Planning Agent**: Analyzes project and creates implementation plan
2. **Coding Agent**: Implements features based on issues
3. **Testing Agent**: Creates and updates test suites
4. **Review Agent**: Creates merge requests and handles merging
5. **Pipeline Agent**: Monitors CI/CD status

All agents share state and coordinate through the supervisor for maximum efficiency.