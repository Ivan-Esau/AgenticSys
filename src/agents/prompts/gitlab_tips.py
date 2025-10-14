"""
GitLab MCP Server tips and best practices for agents.
Handles common issues when using GitLab MCP server tools.
"""

GITLAB_BEST_PRACTICES = """
GITLAB MCP SERVER BEST PRACTICES AND KNOWN ISSUES:

1. FILE CREATION AND CACHING:
   - The MCP server communicates with GitLab API which has caching delays
   - After create_or_update_file() MCP tool call, wait 2-3 seconds before reading
   - Always verify file creation with get_file_contents(ref=branch) MCP tool
   - If file not found, retry after a short delay (up to 3 attempts)

2. MCP TOOL BRANCH OPERATIONS:
   - ALWAYS specify ref=branch_name parameter in MCP tool calls:
     * create_or_update_file(ref=work_branch, commit_message="feat: Add feature", ...)
     * get_file_contents(ref=work_branch, ...)
     * get_repository_tree(ref=work_branch, ...)
   - CRITICAL: create_or_update_file REQUIRES BOTH ref AND commit_message:
     * WRONG: create_or_update_file(ref=work_branch, file_path="...", content="...")
     * CORRECT: create_or_update_file(ref=work_branch, commit_message="feat: Add feature", file_path="...", content="...")
   - The MCP server needs explicit branch references
   - Never assume default branch, always be explicit

3. COMMIT AND PUSH PATTERNS:
   - Group related files in single commits when possible
   - Use descriptive commit messages
   - After commits, allow time for GitLab to process (2-3 seconds)

4. PIPELINE MONITORING:
   - Pipelines may take 10-30 seconds to start after push
   - CRITICAL: Wait at least 30 seconds after commit before checking pipeline
   - Use get_latest_pipeline_for_ref(ref=branch) for branch pipelines
   - Check pipeline status every 30 seconds, not more frequently
   - Maximum wait time: 10 minutes for pipeline completion
   - For network failures: Wait 60 seconds before retry

5. FILE VERIFICATION PROTOCOL:
   After creating files:
   1. Create/update file with ref=branch
   2. Wait 2-3 seconds for API cache
   3. Verify with get_file_contents(ref=branch)
   4. If not found, wait 3 more seconds and retry
   5. After 3 attempts, report issue

6. WORKING WITH JAVA/MAVEN PROJECTS:
   - Create directory structure first (src/main/java/, src/test/java/)
   - Then create files within those directories
   - Update pom.xml dependencies incrementally
   - Allow extra time for Maven dependency resolution in pipelines

7. MERGE REQUEST BEST PRACTICES:
   - Always check if MR already exists before creating
   - Include "Closes #issue_number" in MR description
   - Wait for pipeline to complete before merging
   - Use squash commits for cleaner history

8. ERROR RECOVERY:
   - If "404 Not Found": Check branch name and file path
   - If "409 Conflict": Resource already exists, use update instead
   - If "422 Unprocessable": Check parameters and retry
   - If "500 Server Error": Wait and retry with exponential backoff
   - Connection timeouts: Wait 60s and retry (max 2 times)

9. COMMIT BATCHING TO REDUCE PIPELINE LOAD:
   - Group related files in single commits
   - Avoid triggering pipeline with every file change
   - Wait 30 seconds after commits before checking pipeline
   - Maximum 2-3 commits per issue implementation
   - One commit for implementation, one for tests, one for fixes if needed
"""

def get_gitlab_tips():
    """Return GitLab-specific tips for agents."""
    return GITLAB_BEST_PRACTICES