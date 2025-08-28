# GitLab Agent System

A sophisticated multi-agent AI system that automates GitLab project implementation using advanced LLM orchestration frameworks. Built with LangChain, LangGraph, and multi-provider LLM support for intelligent code generation, testing, and project management.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- GitLab project access
- LLM provider API key (DeepSeek, OpenAI, Claude, etc.)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Create `.env` file with your credentials:
   ```bash
   # GitLab Configuration
   GITLAB_URL=https://gitlab.com
   GITLAB_TOKEN=your_gitlab_token
   
   # Default LLM Provider (DeepSeek recommended)
   LLM_PROVIDER=deepseek
   DEEPSEEK_API_KEY=your_deepseek_api_key
   
   # Alternative providers (optional)
   OPENAI_API_KEY=your_openai_key
   ANTHROPIC_API_KEY=your_claude_key
   GROQ_API_KEY=your_groq_key
   ```

3. **Start MCP server:**
   ```bash
   docker-compose up -d
   ```

4. **Run the system:**
   ```bash
   # Interactive mode (recommended)
   python run.py
   
   # CLI mode examples
   python run.py --project-id 114                    # Analyze only
   python run.py --project-id 114 --apply            # Full implementation
   python run.py --project-id 114 --issue 1 --apply  # Single issue
   ```

## 🏗️ Architecture Overview

### Core Design Patterns

**Supervisor Pattern**: Central orchestrator coordinates specialized agents
**Shared State Management**: Intelligent caching and cross-agent coordination
**ReAct Pattern**: Reasoning and Acting cycles powered by LangGraph
**MCP Integration**: Model Context Protocol for GitLab API communication

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SUPERVISOR CLASS                               │
│                     (Single Instance)                               │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────────────────────────────┐ │
│  │ ProjectState    │    │         MCP Client & Tools              │ │
│  │ - file_cache    │    │  (Initialized once, shared to all)     │ │
│  │ - issue_status  │    │                                         │ │
│  │ - plan          │    │ • get_project    • push_files           │ │
│  │ - checkpoints   │    │ • list_issues    • create_branch        │ │
│  │ - handoff_context│   │ • get_file_contents                     │ │
│  └─────────────────┘    │ • create_merge_request                  │ │
│                          │ • merge_merge_request + state_tools     │ │
│                          └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                │
                     ┌──────────▼──────────┐
                     │   route_task()      │
                     │ (Method dispatches) │
                     └──────────┬──────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│planning_    │         │coding_      │         │review_      │
│agent.run()  │         │agent.run()  │         │agent.run()  │
│             │         │             │         │             │
│Creates      │         │Creates      │         │Creates      │
│BaseAgent    │──────▶  │BaseAgent    │──────▶  │BaseAgent    │
│internally   │         │internally   │         │internally   │
│with tools   │         │with tools   │         │with tools   │
└─────────────┘         └─────────────┘         └─────────────┘
                                │
                                ▼
                        ┌─────────────┐
                        │testing_     │
                        │agent.run()  │
                        │             │
                        │Creates      │
                        │BaseAgent    │
                        │internally   │
                        │with tools   │
                        └─────────────┘

Each Agent Module:
1. Receives: project_id, tools (from supervisor), task params
2. Creates: BaseAgent(name, prompt, tools, model) internally  
3. Calls: agent.run(user_instruction) → LangGraph ReAct execution
4. Returns: String result back to supervisor

Flow: supervisor.route_task() → agent_module.run() → BaseAgent.run() → LangGraph
```

### Project Structure

```
├── run.py                      # 🎯 Main entry point with interactive CLI
├── requirements.txt            # 📦 Python dependencies
├── docker-compose.yml          # 🐳 MCP server configuration
└── src/
    ├── core/                   # 🧠 Core system components
    │   ├── llm/               # 🤖 Multi-provider LLM management
    │   │   ├── llm_providers.py    # Dynamic provider loading
    │   │   ├── model_config_loader.py # JSON-based model configs
    │   │   └── config.py           # System configuration
    │   ├── context/           # 📊 State management
    │   │   ├── state.py           # Shared project state
    │   │   └── state_tools.py     # State-aware utilities
    │   └── agents/            # 🎭 Agent constants and utilities
    ├── agents/                # 🤖 Specialized AI agents
    │   ├── base_agent.py      # Base agent with LangGraph integration
    │   ├── planning_agent.py  # Project analysis and planning
    │   ├── coding_agent.py    # Feature implementation
    │   ├── testing_agent.py   # Test generation and CI/CD
    │   └── review_agent.py    # Code review and merging
    ├── orchestrator/          # 🎼 Agent coordination
    │   └── supervisor.py      # Supervisor pattern implementation
    ├── infrastructure/        # 🔧 External integrations
    │   └── mcp_client.py      # GitLab MCP client wrapper
    └── configs/               # ⚙️ Configuration files
        └── models/            # 🤖 LLM model configurations
            ├── deepseek.json  # DeepSeek models
            ├── openai.json    # OpenAI models
            ├── claude.json    # Anthropic Claude models
            ├── groq.json      # Groq models
            └── ollama.json    # Local Ollama models
```

## 🧠 Core Technologies & Frameworks

### AI/ML Stack
- **LangChain** (v0.3.0+) - Core LLM framework and tool integration
- **LangGraph** (v0.2.0+) - Agent workflow orchestration and ReAct patterns
- **LangChain Adapters** - MCP protocol integration for GitLab tools

### Multi-Provider LLM Support
| Provider | Models | Specialization | Configuration |
|----------|---------|----------------|---------------|
| **DeepSeek** | R1, Chat, Coder | Code generation, reasoning | `deepseek.json` |
| **OpenAI** | GPT-4, GPT-3.5 | General purpose, chat | `openai.json` |
| **Claude** | Sonnet, Haiku, Opus | Analysis, safety-focused | `claude.json` |
| **Groq** | Llama, Mixtral | Fast inference | `groq.json` |
| **Ollama** | Local models | Privacy, offline | `ollama.json` |

### Infrastructure & Development
- **Docker Compose** - MCP server containerization
- **MCP Protocol** - Model Context Protocol for tool communication
- **Async/Await** - Full asynchronous architecture
- **JSON Configs** - Dynamic model and provider configuration
- **Type Hints** - Complete Python type annotations

## 🤖 Agent System Architecture

### Specialized Agents

#### 🎯 Planning Agent
- **Purpose**: Project analysis and implementation strategy
- **Capabilities**: 
  - Repository structure analysis
  - Issue prioritization and dependency mapping
  - Technology stack detection
  - Implementation roadmap creation
- **Model**: Task-optimized for reasoning (Claude Sonnet, DeepSeek R1)

#### 💻 Coding Agent  
- **Purpose**: Feature implementation and code generation
- **Capabilities**:
  - Multi-language code generation
  - Branch creation and management
  - File modification and creation
  - Code structure analysis
- **Model**: Specialized coding models (DeepSeek Coder, GPT-4)

#### 🧪 Testing Agent
- **Purpose**: Test suite creation and CI/CD management
- **Capabilities**:
  - Unit test generation
  - Integration test creation
  - CI/CD pipeline monitoring
  - Test failure analysis and fixes
- **Model**: Deterministic models for consistent test generation

#### 🔍 Review Agent
- **Purpose**: Code review and merge request management
- **Capabilities**:
  - Merge request creation
  - Code quality assessment
  - Pipeline status monitoring
  - Automated merging
- **Model**: Balanced models for code analysis

#### 🎼 Supervisor
- **Purpose**: Central orchestration and coordination
- **Capabilities**:
  - Agent workflow management
  - State synchronization
  - Error handling and retry logic
  - Resource optimization
- **Pattern**: Supervisor pattern with shared state

### Advanced Features

#### 🧠 Intelligent State Management
```python
class ProjectState:
    - file_cache: Dict[str, str]      # Cached file contents
    - issue_status: Dict[str, str]    # Issue implementation tracking
    - plan: Dict[str, Any]           # Generated implementation plan
    - checkpoints: List[Dict]        # State snapshots
    - handoff_context: Dict          # Agent-to-agent communication
```

#### 🔄 Self-Healing Pipeline
- **Pipeline Failure Detection**: Automatic CI/CD failure recognition
- **Intelligent Routing**: Route failures to appropriate agents
- **Retry Logic**: Configurable retry strategies with backoff
- **Error Context**: Preserve error details for targeted fixes

#### 📊 Multi-Model Task Optimization
```json
{
  "task_preferences": {
    "coding": "claude-3-5-sonnet",
    "testing": "claude-3-5-sonnet", 
    "planning": "claude-3-5-haiku",
    "review": "claude-3-5-haiku",
    "debugging": "deepseek-coder",
    "analysis": "deepseek-r1"
  }
}
```

## 🎮 Usage Modes

### Interactive Mode (Recommended)
```bash
python run.py
```
- Full menu-driven configuration
- LLM provider selection
- Tech stack configuration
- Step-by-step guidance

### CLI Mode (Advanced)
```bash
# Analysis only
python run.py --project-id 114

# Full implementation with tech stack
python run.py --project-id 114 --apply --backend-lang python --frontend-lang react

# Specific LLM provider
python run.py --project-id 114 --apply --llm-provider claude --llm-model claude-3-5-sonnet

# Resume from saved state
python run.py --project-id 114 --resume state_file.json

# Single issue implementation
python run.py --project-id 114 --issue 42 --apply
```

## ⚙️ Configuration

### Environment Variables
```bash
# Core Configuration
LLM_PROVIDER=deepseek                    # Default LLM provider
LLM_TEMPERATURE=0.3                      # Default temperature
LLM_MAX_RETRIES=5                        # Retry attempts

# GitLab Integration
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_access_token

# Provider API Keys
DEEPSEEK_API_KEY=your_key
OPENAI_API_KEY=your_key  
ANTHROPIC_API_KEY=your_key
GROQ_API_KEY=your_key
```

### Model Configuration
Each provider has a JSON configuration file in `src/configs/models/`:

```json
{
  "provider": "deepseek",
  "display_name": "DeepSeek AI",
  "api_key_env": "DEEPSEEK_API_KEY",
  "models": {
    "deepseek-r1": {
      "display_name": "DeepSeek R1",
      "description": "Advanced reasoning model",
      "context_length": 65536,
      "recommended_for": ["reasoning", "planning"]
    }
  },
  "task_preferences": {
    "coding": "deepseek-coder",
    "planning": "deepseek-r1"
  }
}
```

## 🔧 Advanced Features

### State Persistence & Resume
- **Automatic Checkpoints**: State saved after each major operation
- **Resume Capability**: Continue from any saved state
- **Error Recovery**: Rollback to previous stable state on failures

### Intelligent Caching
- **File Content Caching**: Reduce GitLab API calls
- **Cross-Agent Sharing**: Cached data available to all agents
- **Smart Invalidation**: Cache updates on file modifications

### Pipeline Integration
- **CI/CD Monitoring**: Real-time pipeline status tracking
- **Failure Analysis**: Automatic error pattern recognition
- **Self-Healing**: Automated fix attempts for common failures

### Multi-Technology Support
- **Auto-Detection**: Automatic tech stack identification
- **Manual Override**: Configure tech stack for new projects
- **Framework-Specific**: Tailored implementation patterns

## 🚀 Performance & Optimization

### Concurrency
- **Async Architecture**: Full async/await implementation
- **Parallel Tool Calls**: Concurrent GitLab API operations
- **Agent Pipelining**: Overlapped agent execution where possible

### Cost Optimization
- **Model Selection**: Task-appropriate model routing
- **Context Management**: Intelligent context window usage
- **Caching Strategy**: Minimize redundant LLM calls

### Reliability
- **Error Handling**: Comprehensive exception management  
- **Retry Logic**: Configurable retry strategies
- **Fallback Systems**: Graceful degradation on failures

## 📈 Monitoring & Debugging

### Agent Metrics
```
Agent Performance:
  planning: 15 calls, 1 errors (6.7%)
  coding: 42 calls, 3 errors (7.1%) 
  testing: 28 calls, 2 errors (7.1%)
  review: 31 calls, 0 errors (0.0%)
```

### Debug Mode
```bash
python run.py --project-id 114 --debug
```
- Detailed execution logs
- Full stack traces on errors
- Token usage statistics
- State transition tracking

## 🎯 Use Cases

### Development Automation
- **Feature Implementation**: Automated coding from GitLab issues
- **Test Generation**: Comprehensive test suite creation
- **Code Review**: Automated merge request management
- **CI/CD Integration**: Pipeline monitoring and fixing

### Project Management
- **Issue Analysis**: Intelligent issue prioritization
- **Dependency Mapping**: Implementation order optimization
- **Progress Tracking**: Real-time implementation status
- **State Management**: Persistent execution state

### Team Productivity  
- **Consistent Implementation**: Standardized coding patterns
- **Quality Assurance**: Automated testing and review
- **Documentation**: Self-documenting implementation process
- **Knowledge Transfer**: Persistent project understanding

## 🤝 Contributing

### Development Setup
1. Clone repository
2. Install development dependencies: `pip install -r requirements.txt`
3. Run tests: `pytest`
4. Format code: `black src/`
5. Type check: `mypy src/`

### Architecture Guidelines
- Follow the Supervisor pattern for agent coordination
- Use shared state for cross-agent communication
- Implement proper error handling and retry logic
- Add comprehensive type hints
- Update model configurations for new providers

## 📄 License

[License information here]

## 🆘 Support

- **Issues**: Report bugs and feature requests
- **Documentation**: Check inline code documentation
- **Debug**: Use `--debug` flag for detailed logging
- **State**: Examine saved state files for troubleshooting

---

*Built with ❤️ using LangChain, LangGraph, and modern AI agent orchestration patterns*