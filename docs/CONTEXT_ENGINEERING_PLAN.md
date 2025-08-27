# Context Engineering Plan

## Problem
Current agents read far more context than needed:
- **Planning Agent**: Reads "ALL existing source files" 
- **Coding Agent**: Re-reads files Planning already analyzed
- **Testing Agent**: Re-scans test directories 
- **Review Agent**: Could just see the diff

## Solution: Contextual Intelligence

### 1. Planning Agent - High-Level Context Only
**Current**: Reads all source files
**Better**: Only needs project overview
```
files_to_read = [
    'README.md',         # Project description
    'package.json',      # Dependencies/scripts  
    'requirements.txt',  # Python deps
    'docker-compose.yml' # Architecture
]
directories_to_scan = [
    '.',    # Root structure only
    'src'   # Directory names, not file contents
]
```
**Result**: ~90% less file reading for planning

### 2. Coding Agent - Task-Specific Context  
**Current**: Re-reads everything
**Better**: Only files for specific issue
```python
def get_coding_context(issue):
    return {
        'files_to_read': issue['files_to_modify'],
        'related_files': find_imports_and_deps(issue['files_to_modify']),
        'config_files': ['package.json']  # Only if needed
    }
```
**Result**: Read only 3-5 files instead of entire codebase

### 3. Testing Agent - Test-Focused Context
**Current**: Scans all test directories
**Better**: Only test files for components being tested
```python
def get_testing_context(files_being_tested):
    return {
        'files_to_read': files_being_tested + find_test_files_for(files_being_tested),
        'test_configs': ['jest.config.js', 'pytest.ini'],
        'existing_patterns': scan_test_directory_structure()
    }
```
**Result**: Read only relevant test files

### 4. Review Agent - Change-Only Context
**Current**: Might read whole codebase  
**Better**: Only the diff
```python
def get_review_context(branch):
    return {
        'files_to_read': get_changed_files(branch),
        'context_files': []  # Usually none needed
    }
```
**Result**: Minimal context, fastest execution

## Implementation Strategy

### Phase 1: Smart Planning Agent
Update `planning_agent.py` to use `ContextEngine`:
```python
# Instead of: "Read ALL existing source files"
context_plan = get_context_for_agent('planning', project_id)
# Read only: README, package.json, directory structure
```

### Phase 2: Contextual Handoffs
Planning agent creates **context inheritance** for next agents:
```python
handoff_data = {
    'files_relevant_to_issue_1': ['src/game.py', 'src/snake.py'],
    'files_relevant_to_issue_2': ['src/ui.py', 'src/renderer.py'],
    'test_files_needed': ['test_game.py', 'test_snake.py']
}
```

### Phase 3: Smart State Caching
Cache only what's actually needed:
```python
# Instead of caching everything:
state.cache_context_for_issue(issue_id, relevant_files_only)
```

## Expected Benefits

1. **Massive Context Reduction**: 
   - Planning: 90% less file reading
   - Coding: 80% less file reading  
   - Testing: 70% less file reading
   
2. **Faster Agent Execution**:
   - Less time reading files
   - Less LLM context processing
   - Faster decision making
   
3. **More Focused Agents**:
   - Agents see only what they need
   - Better reasoning with relevant context
   - Less confusion from irrelevant code

4. **Intelligent Caching**:
   - Cache files by purpose/component
   - Share relevant context between agents
   - Eliminate redundant reads

## Next Steps

1. **Update Planning Agent** with contextual intelligence
2. **Implement handoff context** from planning to coding
3. **Test with real project** to measure improvement
4. **Extend to all agents** based on results

This shifts from "cache everything" to "read only what you need" - much more efficient!