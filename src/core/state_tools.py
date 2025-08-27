"""
State-aware tools that integrate ProjectState with LangChain tool annotations.
These tools provide intelligent, context-aware operations for agents.
"""

from typing import Annotated, List, Optional, Dict, Any
from langchain_core.tools import tool
from .state import ProjectState, get_project_state


@tool  
def get_file_with_context(
    file_path: Annotated[str, "Path to file to read"], 
    project_id: Annotated[str, "Project ID for state context"]
) -> str:
    """
    Get file contents with intelligent caching and context awareness.
    This is a STATE-AWARE tool that provides context along with file content.
    
    NOTE: This tool only provides state context. For actual file reading,
    use the regular get_file_contents tool (which has caching built-in).
    """
    state = get_project_state(project_id)
    
    # Check cache first  
    cached_content = state.get_cached_file(file_path)
    if cached_content:
        print(f"  [STATE CACHE HIT] {file_path}")
        
        # Add contextual information
        context_info = []
        
        # Check if file is related to current issue
        if state.current_issue:
            current_issue = next((issue for issue in state.issues if issue.get('iid') == state.current_issue), None)
            if current_issue and file_path in current_issue.get('files_to_modify', []):
                context_info.append(f"[CONTEXT] File is target for current issue: {current_issue.get('title')}")
        
        # Check implementation status
        impl_status = state.get_file_implementation_status(file_path)
        if impl_status != 'unknown':
            context_info.append(f"[STATUS] Implementation: {impl_status}")
        
        # Return content with context
        context_header = "\n".join(context_info) + "\n\n" if context_info else ""
        return f"{context_header}{cached_content}"
    
    # File not cached - provide guidance 
    print(f"  [STATE CACHE MISS] {file_path}")
    return f"[STATE] File {file_path} not in state cache. Use get_file_contents to read it first, then this tool will provide context."


@tool  
def get_project_context(
    project_id: Annotated[str, "Project ID"]
) -> str:
    """
    Get comprehensive project context including current state, issues, and progress.
    This gives agents full situational awareness.
    """
    state = get_project_state(project_id)
    
    context = {
        "project_id": project_id,
        "thread_id": state.thread_id,
        "default_branch": state.default_branch,
        "current_branch": state.current_branch,
        "current_issue": state.current_issue,
        "total_issues": len(state.issues),
        "completed_issues": len(state.completed_issues),
        "cached_files": len(state.file_cache),
        "implementation_progress": f"{len(state.completed_issues)}/{len(state.issues)} complete",
        "tech_stack": state.tech_stack if state.tech_stack else "auto-detect"
    }
    
    # Add current issue details if available
    if state.current_issue:
        current_issue = next((issue for issue in state.issues if issue.get('iid') == state.current_issue), None)
        if current_issue:
            context["current_issue_title"] = current_issue.get('title')
            context["current_issue_files"] = current_issue.get('files_to_modify', [])
    
    return f"[PROJECT CONTEXT] {context}"


@tool
def check_issue_dependencies(
    issue_id: Annotated[str, "Issue ID to check"], 
    project_id: Annotated[str, "Project ID"]
) -> str:
    """
    Check if issue has dependencies that need to be completed first.
    Provides intelligent workflow ordering.
    """
    state = get_project_state(project_id)
    
    # Find the issue
    issue = next((issue for issue in state.issues if str(issue.get('iid')) == str(issue_id)), None)
    if not issue:
        return f"[ERROR] Issue {issue_id} not found in project state"
    
    # Check dependencies
    dependencies = issue.get('dependencies', [])
    if not dependencies:
        return f"[DEPENDENCIES] Issue {issue_id} has no dependencies - ready to implement"
    
    # Check which dependencies are complete
    incomplete_deps = []
    for dep_id in dependencies:
        if dep_id not in state.completed_issues:
            incomplete_deps.append(dep_id)
    
    if incomplete_deps:
        return f"[DEPENDENCIES] Issue {issue_id} blocked by incomplete dependencies: {incomplete_deps}"
    else:
        return f"[DEPENDENCIES] Issue {issue_id} dependencies complete - ready to implement"


@tool
def get_implementation_context(
    file_path: Annotated[str, "File path to analyze"],
    project_id: Annotated[str, "Project ID"]
) -> str:
    """
    Get rich implementation context for a file - what needs to be done, 
    what exists, what's related.
    """
    state = get_project_state(project_id)
    
    context = []
    
    # Check if file exists in cache
    cached_content = state.get_cached_file(file_path)
    if cached_content:
        # Analyze implementation status
        impl_status = state._analyze_file_status(cached_content)
        context.append(f"[FILE STATUS] {impl_status}")
        
        # Check size/complexity
        lines = len(cached_content.split('\n'))
        context.append(f"[SIZE] {lines} lines")
    else:
        context.append(f"[FILE STATUS] Not cached - unknown state")
    
    # Check if file is mentioned in issues
    related_issues = []
    for issue in state.issues:
        if file_path in issue.get('files_to_modify', []) or file_path in issue.get('files_to_create', []):
            related_issues.append(issue.get('title', 'Unknown'))
    
    if related_issues:
        context.append(f"[RELATED ISSUES] {', '.join(related_issues)}")
    
    # Check implementation order
    if state.current_issue:
        current_issue = next((issue for issue in state.issues if issue.get('iid') == state.current_issue), None)
        if current_issue and file_path in current_issue.get('files_to_modify', []):
            context.append(f"[CURRENT TASK] File is target for active issue")
    
    return "\n".join(context)


@tool
def update_implementation_progress(
    issue_id: Annotated[str, "Issue ID that was completed"],
    project_id: Annotated[str, "Project ID"],
    files_modified: Annotated[List[str], "List of files that were modified"],
    status: Annotated[str, "New status: complete, partial, failed"] = "complete"
) -> str:
    """
    Update project state with implementation progress.
    Allows agents to maintain accurate project state.
    """
    state = get_project_state(project_id)
    
    # Update issue status
    state.update_issue_status(issue_id, status)
    
    # Update file statuses based on what was modified
    for file_path in files_modified:
        state.update_file_implementation_status(file_path, status)
    
    # Calculate overall progress
    progress = f"{len(state.completed_issues)}/{len(state.issues)} issues complete"
    
    return f"[PROGRESS UPDATE] Issue {issue_id} -> {status}. Files: {files_modified}. Progress: {progress}"


# Helper function to get all state-aware tools
def get_state_aware_tools() -> List:
    """Get all state-aware tools for use in agents"""
    return [
        get_file_with_context,
        get_project_context, 
        check_issue_dependencies,
        get_implementation_context,
        update_implementation_progress
    ]