"""
API routes for the AgenticSys Web GUI
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import os
import json
import traceback
from datetime import datetime

from .models import (
    SystemConfig, SystemStatus, APIResponse,
    ProjectInfo, IssueStatus
)

router = APIRouter()

# Store for system state (will be replaced with proper state management)
system_state = {
    "config": None,
    "status": None,
    "orchestrator": None
}


@router.post("/system/start", response_model=APIResponse)
async def start_system(config: SystemConfig):
    """Start the autonomous system with given configuration"""
    try:
        # Import here to avoid circular imports
        from ..core.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()

        # Validate project ID
        if not config.project_id:
            raise HTTPException(status_code=400, detail="Project ID is required")

        # Start the system
        await orchestrator.start(config.dict())

        return APIResponse(
            success=True,
            message="System started successfully",
            data={"config": config.dict()}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/stop", response_model=APIResponse)
async def stop_system():
    """Stop the running system"""
    try:
        from ..core.orchestrator import get_orchestrator

        orchestrator = get_orchestrator()
        await orchestrator.stop()

        return APIResponse(
            success=True,
            message="System stopped successfully",
            data=None
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/status", response_model=SystemStatus)
async def get_system_status():
    """Get current system status"""
    from web_gui.backend.core.orchestrator import get_orchestrator

    orchestrator = get_orchestrator()
    status = orchestrator.get_status()

    return SystemStatus(**status)


@router.get("/projects", response_model=List[ProjectInfo])
async def get_projects():
    """Get list of available GitLab projects"""
    try:
        projects = []

        # Try to get projects via MCP client
        try:
            from src.infrastructure.mcp_client import load_mcp_tools

            # Load MCP tools
            tools, client = await load_mcp_tools()

            # Find the list_projects tool
            list_projects_tool = None
            for tool in tools:
                if hasattr(tool, 'name'):
                    print(f"[DEBUG] Found tool: {tool.name}")
                    if tool.name == 'list_projects':
                        list_projects_tool = tool
                        break

            if list_projects_tool:
                # Invoke the tool to get projects
                print("[INFO] Calling list_projects tool")
                result = await list_projects_tool.ainvoke({
                    'include_archived': False,
                    'order_by': 'last_activity_at',
                    'sort': 'desc'
                })

                print(f"[DEBUG] Tool result type: {type(result)}")

                # Parse the result
                if result:
                    # The result might be a string (JSON) or already parsed
                    import json
                    if isinstance(result, str):
                        try:
                            parsed_result = json.loads(result)
                        except:
                            parsed_result = result
                    else:
                        parsed_result = result

                    # Extract projects from the result
                    if isinstance(parsed_result, list):
                        project_list = parsed_result
                    elif isinstance(parsed_result, dict) and 'projects' in parsed_result:
                        project_list = parsed_result['projects']
                    else:
                        project_list = []

                    # Convert to ProjectInfo objects
                    for proj in project_list[:20]:  # Limit to 20 projects
                        if isinstance(proj, dict):
                            projects.append(ProjectInfo(
                                id=str(proj.get('id', '')),
                                name=proj.get('name_with_namespace', proj.get('name', '')),
                                description=proj.get('description', '') or '',
                                default_branch=proj.get('default_branch', 'main'),
                                web_url=proj.get('web_url', ''),
                                issues_count=proj.get('open_issues_count', 0),
                                open_issues=proj.get('open_issues_count', 0)
                            ))

                    print(f"[INFO] Loaded {len(projects)} projects from GitLab")
            else:
                print("[WARN] gitlab_list_projects tool not found")

        except Exception as e:
            print(f"[ERROR] Failed to load projects via MCP: {e}")
            import traceback
            traceback.print_exc()

        # Fallback: Check if there's a project configured in environment
        if not projects:
            gitlab_project = os.getenv("GITLAB_PROJECT_ID")
            if gitlab_project:
                projects.append(ProjectInfo(
                    id=gitlab_project,
                    name=f"Project {gitlab_project}",
                    description="Environment configured project",
                    default_branch="main",
                    web_url=f"{os.getenv('GITLAB_URL', 'https://gitlab.com')}/projects/{gitlab_project}",
                    issues_count=0,
                    open_issues=0
                ))

        return projects

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/issues")
async def get_project_issues(project_id: str, state: str = "opened"):
    """Get issues for a specific project"""
    try:
        issues = []

        # Try to get issues via MCP client
        try:
            from src.infrastructure.mcp_client import load_mcp_tools
            tools, client = await load_mcp_tools()

            # Look for the list_issues tool
            for tool in tools:
                if hasattr(tool, 'name'):
                    # Use the list_issues tool
                    if tool.name == 'list_issues':
                        result = await tool.ainvoke({
                            'project_id': project_id,
                            'state': state
                        })

                        # Parse result (might be JSON string)
                        if result:
                            if isinstance(result, str):
                                try:
                                    result = json.loads(result)
                                except:
                                    pass

                            if isinstance(result, list):
                                issue_list = result
                            else:
                                issue_list = []

                            for issue in issue_list[:20]:  # Limit to 20 issues
                                issues.append({
                                    'id': issue.get('id', ''),
                                    'iid': issue.get('iid', ''),
                                    'title': issue.get('title', ''),
                                    'description': issue.get('description', ''),
                                    'state': issue.get('state', 'opened'),
                                    'labels': issue.get('labels', []),
                                    'assignee': issue.get('assignee', {}).get('name', '') if issue.get('assignee') else '',
                                    'web_url': issue.get('web_url', ''),
                                    'created_at': issue.get('created_at', ''),
                                    'updated_at': issue.get('updated_at', '')
                                })
                            break
        except Exception as e:
            print(f"[INFO] MCP client not available for issues: {e}")
            # Return mock data if MCP is not available
            issues = [
                {
                    'id': '1',
                    'iid': '1',
                    'title': 'Sample Issue #1: Implement user authentication',
                    'description': 'Add JWT-based authentication to the API',
                    'state': 'opened',
                    'labels': ['feature', 'backend'],
                    'assignee': '',
                    'web_url': '#',
                    'created_at': '2024-01-01',
                    'updated_at': '2024-01-02'
                },
                {
                    'id': '2',
                    'iid': '2',
                    'title': 'Sample Issue #2: Fix database connection timeout',
                    'description': 'Connection pool exhaustion under load',
                    'state': 'opened',
                    'labels': ['bug', 'database'],
                    'assignee': '',
                    'web_url': '#',
                    'created_at': '2024-01-03',
                    'updated_at': '2024-01-04'
                }
            ]

        return issues

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/detect-tech")
async def detect_tech_stack(project_id: str):
    """Auto-detect technology stack for a project"""
    try:
        tech_stack = {
            "language": "Python",
            "framework": None,
            "database": None,
            "testing": "pytest",
            "deployment": None,
            "ci_cd": "GitLab CI"
        }

        # Try to detect tech stack via MCP client
        try:
            from src.infrastructure.mcp_client import get_common_tools_and_client
            tools, client = await get_common_tools_and_client()

            # Look for a tool that can get project files
            for tool in tools:
                if hasattr(tool, 'name'):
                    # Try to get repository tree or files
                    if 'get_file' in tool.name.lower() or 'repository_tree' in tool.name.lower():
                        # Try to get common config files to detect tech stack
                        files_to_check = [
                            'package.json',
                            'requirements.txt',
                            'pyproject.toml',
                            'pom.xml',
                            'build.gradle',
                            'Gemfile',
                            'composer.json',
                            'go.mod',
                            'Cargo.toml'
                        ]

                        for file in files_to_check:
                            try:
                                result = await tool.invoke({
                                    'project_id': project_id,
                                    'file_path': file,
                                    'ref': 'main'
                                })

                                if result:
                                    # Analyze file content to detect tech stack
                                    content = str(result)

                                    if file == 'package.json':
                                        tech_stack['language'] = 'JavaScript'
                                        if 'react' in content.lower():
                                            tech_stack['framework'] = 'React'
                                        elif 'vue' in content.lower():
                                            tech_stack['framework'] = 'Vue.js'
                                        elif 'angular' in content.lower():
                                            tech_stack['framework'] = 'Angular'
                                        elif 'express' in content.lower():
                                            tech_stack['framework'] = 'Express.js'
                                        if 'jest' in content.lower():
                                            tech_stack['testing'] = 'Jest'
                                        elif 'mocha' in content.lower():
                                            tech_stack['testing'] = 'Mocha'

                                    elif file in ['requirements.txt', 'pyproject.toml']:
                                        tech_stack['language'] = 'Python'
                                        if 'fastapi' in content.lower():
                                            tech_stack['framework'] = 'FastAPI'
                                        elif 'django' in content.lower():
                                            tech_stack['framework'] = 'Django'
                                        elif 'flask' in content.lower():
                                            tech_stack['framework'] = 'Flask'
                                        if 'postgresql' in content.lower() or 'psycopg' in content.lower():
                                            tech_stack['database'] = 'PostgreSQL'
                                        elif 'mysql' in content.lower() or 'pymysql' in content.lower():
                                            tech_stack['database'] = 'MySQL'
                                        elif 'mongodb' in content.lower() or 'pymongo' in content.lower():
                                            tech_stack['database'] = 'MongoDB'
                                        if 'pytest' in content.lower():
                                            tech_stack['testing'] = 'pytest'
                                        elif 'unittest' in content.lower():
                                            tech_stack['testing'] = 'unittest'

                                    elif file == 'pom.xml' or file == 'build.gradle':
                                        tech_stack['language'] = 'Java'
                                        if 'spring' in content.lower():
                                            tech_stack['framework'] = 'Spring Boot'
                                        if 'junit' in content.lower():
                                            tech_stack['testing'] = 'JUnit'

                                    elif file == 'Gemfile':
                                        tech_stack['language'] = 'Ruby'
                                        if 'rails' in content.lower():
                                            tech_stack['framework'] = 'Ruby on Rails'
                                        if 'rspec' in content.lower():
                                            tech_stack['testing'] = 'RSpec'

                                    elif file == 'go.mod':
                                        tech_stack['language'] = 'Go'
                                        if 'gin' in content.lower():
                                            tech_stack['framework'] = 'Gin'
                                        elif 'echo' in content.lower():
                                            tech_stack['framework'] = 'Echo'

                                    # Check for Docker
                                    if 'docker' in content.lower():
                                        tech_stack['deployment'] = 'Docker'

                            except:
                                continue
                        break
        except Exception as e:
            print(f"[INFO] Could not auto-detect tech stack: {e}")

        return tech_stack  # Return plain dict (TechStack model removed)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def get_agents_info():
    """Get information about available agents"""
    return {
        "agents": [
            {
                "name": "Planning Agent",
                "description": "Creates implementation plans from issues",
                "status": "idle"
            },
            {
                "name": "Coding Agent",
                "description": "Implements the planned solution",
                "status": "idle"
            },
            {
                "name": "Testing Agent",
                "description": "Creates and runs tests",
                "status": "idle"
            },
            {
                "name": "Review Agent",
                "description": "Reviews code and creates merge requests",
                "status": "idle"
            }
        ]
    }


@router.get("/config/defaults")
async def get_default_config():
    """Get default configuration values"""
    return {
        "mode": "implement_all",
        "auto_merge": False,
        "debug": False,
        "min_coverage": 70.0,
        "tech_stack": {
            "language": "Python",
            "testing": "pytest",
            "ci_cd": "GitLab CI"
        }
    }


@router.get("/stats")
async def get_statistics():
    """Get system statistics"""
    from web_gui.backend.core.orchestrator import get_orchestrator

    orchestrator = get_orchestrator()
    return orchestrator.get_statistics()


# LLM Configuration Endpoints
@router.get("/llm/providers")
async def get_llm_providers():
    """Get available LLM providers"""
    try:
        from src.core.llm.llm_providers import Providers

        providers = Providers.get_all()
        default_provider = Providers.get_default()

        print(f"[DEBUG] LLM providers loaded: {providers}, default: {default_provider}")
        return {
            "providers": providers,
            "default": default_provider
        }
    except Exception as e:
        print(f"[ERROR] Failed to get LLM providers: {e}")
        import traceback
        traceback.print_exc()
        return {
            "providers": ["deepseek", "openai", "ollama"],
            "default": "deepseek"
        }


@router.get("/llm/models/{provider}")
async def get_llm_models(provider: str):
    """Get available models for a specific provider"""
    try:
        from src.core.llm.llm_providers import ModelConfigs, LLMProviderConfig

        models = ModelConfigs.get_models_for_provider(provider)
        default_model = LLMProviderConfig.get_default_model_for_provider(provider)

        print(f"[DEBUG] LLM models for {provider}: {models}, default: {default_model}")
        return {
            "models": models,
            "default": default_model
        }
    except Exception as e:
        print(f"[ERROR] Failed to get models for provider {provider}: {e}")
        import traceback
        traceback.print_exc()
        # Return fallback data
        fallback_models = {
            "deepseek": {"deepseek-chat": "DeepSeek Chat", "deepseek-coder": "DeepSeek Coder"},
            "openai": {"gpt-4": "GPT-4", "gpt-3.5-turbo": "GPT-3.5 Turbo"},
            "ollama": {"llama2": "Llama 2", "codellama": "Code Llama"}
        }
        print(f"[DEBUG] Using fallback models for {provider}: {fallback_models.get(provider, {})}")
        return {
            "models": fallback_models.get(provider, {}),
            "default": list(fallback_models.get(provider, {}).keys())[0] if fallback_models.get(provider) else None
        }


@router.get("/llm/current")
async def get_current_llm_config():
    """Get current LLM configuration"""
    try:
        from src.core.llm.llm_providers import LLMProviderConfig
        import os

        current_provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
        current_model = os.getenv("LLM_MODEL", "")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

        if not current_model:
            current_model = LLMProviderConfig.get_default_model_for_provider(current_provider)

        print(f"[DEBUG] Current LLM config: provider={current_provider}, model={current_model}, temp={temperature}")
        return {
            "provider": current_provider,
            "model": current_model,
            "temperature": temperature
        }
    except Exception as e:
        print(f"[ERROR] Failed to get current LLM config: {e}")
        import traceback
        traceback.print_exc()
        config = {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "temperature": 0.7
        }
        print(f"[DEBUG] Using fallback LLM config: {config}")
        return config