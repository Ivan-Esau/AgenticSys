"""
Safe tool wrappers to enforce validation before dangerous operations.
Prevents agents from performing actions that violate system constraints.
"""

import asyncio
from typing import List, Any, Dict
from langchain_core.tools import StructuredTool


def extract_exception_from_group(exc: Exception) -> str:
    """
    Extract meaningful error message from ExceptionGroup/TaskGroup exceptions.

    Python 3.11+ uses TaskGroup which raises ExceptionGroup on failures.
    This function extracts the actual underlying exceptions.

    Args:
        exc: The exception to extract from

    Returns:
        String representation of the underlying error(s)
    """
    # Handle ExceptionGroup (Python 3.11+)
    if hasattr(exc, 'exceptions') and hasattr(exc, '__iter__'):
        underlying_errors = []
        try:
            for sub_exc in exc.exceptions:
                # Recursively extract from nested ExceptionGroups
                if hasattr(sub_exc, 'exceptions'):
                    underlying_errors.append(extract_exception_from_group(sub_exc))
                else:
                    underlying_errors.append(f"{type(sub_exc).__name__}: {str(sub_exc)}")
        except:
            pass

        if underlying_errors:
            return " | ".join(underlying_errors)

    # Fallback to string representation
    return str(exc)


def create_safe_merge_tool(
    merge_tool: StructuredTool,
    get_mr_tool: StructuredTool,
    get_pipeline_tool: StructuredTool,
    get_jobs_tool: StructuredTool
) -> StructuredTool:
    """
    Create a safe wrapper around merge_merge_request that validates BEFORE merging.

    Validation checks (ALL must pass):
    1. Pipeline status must be "success"
    2. All pipeline jobs must have status "success"
    3. MR merge_status must be "can_be_merged"

    Args:
        merge_tool: Original merge_merge_request tool
        get_mr_tool: Tool to get MR details
        get_pipeline_tool: Tool to get latest pipeline
        get_jobs_tool: Tool to get pipeline jobs

    Returns:
        Wrapped tool with validation
    """

    async def safe_merge_merge_request(
        project_id: str,
        mr_iid: int,
        merge_commit_message: str = None,
        skip_validation: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Safe merge that validates pipeline success BEFORE merging.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID
            merge_commit_message: Optional commit message
            skip_validation: If True, skip validation and merge directly.
                           Use this when you've already verified conditions manually.

        Returns error dict if validation fails, merge result if successful.
        """
        # FAST PATH: Skip validation if agent has already verified conditions
        if skip_validation:
            print(f"\n[SAFE-MERGE] Skipping validation (agent pre-verified) - merging MR #{mr_iid} directly...")
            merge_params = {
                "project_id": project_id,
                "mr_iid": mr_iid
            }
            if merge_commit_message:
                merge_params["merge_commit_message"] = merge_commit_message
            merge_params.update(kwargs)

            try:
                result = await merge_tool.ainvoke(merge_params)
                print(f"[SAFE-MERGE] [OK] Merge completed successfully (validation skipped)")
                return result
            except Exception as e:
                error_msg = f"[X] MERGE FAILED: {extract_exception_from_group(e)}"
                print(f"[SAFE-MERGE] {error_msg}")
                return {"error": error_msg, "blocked": True}

        print(f"\n[SAFE-MERGE] Validating MR #{mr_iid} before merge...")

        # STEP 1: Get MR details (with advanced retry logic for MCP TaskGroup exceptions)
        # Exponential backoff: reduces collision with concurrent operations
        # Max retries: 10 attempts with exponential backoff (2, 4, 8, 16, 20, 20, 20...)
        # Rationale: If pipeline succeeded, merge WILL succeed once MCP recovers
        max_retries = 10
        base_retry_delay = 2  # Start with 2 seconds
        max_delay = 20  # Cap at 20 seconds
        mr_result = None

        for attempt in range(max_retries):
            try:
                # Shield MCP operation from external cancellation
                # This protects against interference from concurrent tasks
                mr_result = await asyncio.shield(
                    get_mr_tool.ainvoke({
                        "project_id": project_id,
                        "mr_iid": mr_iid
                    })
                )

                # Handle both dict and string responses
                if isinstance(mr_result, str):
                    import json
                    mr = json.loads(mr_result)
                else:
                    mr = mr_result

                # Success - break out of retry loop
                print(f"[SAFE-MERGE] [OK] get_merge_request succeeded on attempt {attempt + 1}")
                break

            except Exception as e:
                # Extract underlying error from ExceptionGroup/TaskGroup
                underlying_error = extract_exception_from_group(e)
                error_str = str(e)

                # Check if this is a retryable error
                is_taskgroup_error = "TaskGroup" in error_str or "ExceptionGroup" in error_str

                if is_taskgroup_error and attempt < max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = min(base_retry_delay * (2 ** attempt), max_delay)

                    print(f"[SAFE-MERGE] [WARN] MCP get_merge_request failed (attempt {attempt + 1}/{max_retries})")
                    print(f"[SAFE-MERGE] [ERROR] {underlying_error}")
                    print(f"[SAFE-MERGE] [RETRY] Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed or non-retryable error
                    error_msg = f"[X] MERGE BLOCKED: Failed to get MR details after {attempt + 1} attempts: {underlying_error}"
                    print(f"[SAFE-MERGE] {error_msg}")
                    return {"error": error_msg, "blocked": True}

        source_branch = mr.get('source_branch')
        if not source_branch:
            error_msg = f"[X] MERGE BLOCKED: Could not determine source branch"
            print(f"[SAFE-MERGE] {error_msg}")
            return {"error": error_msg, "blocked": True}

        # STEP 2: Get latest pipeline for MR's source branch (with advanced retry logic)
        pipeline_result = None

        for attempt in range(max_retries):
            try:
                # Shield from external cancellation
                pipeline_result = await asyncio.shield(
                    get_pipeline_tool.ainvoke({
                        "project_id": project_id,
                        "ref": source_branch
                    })
                )

                # Handle both dict and string responses
                if isinstance(pipeline_result, str):
                    import json
                    pipeline = json.loads(pipeline_result)
                else:
                    pipeline = pipeline_result

                # Success - break out of retry loop
                print(f"[SAFE-MERGE] [OK] get_pipeline succeeded on attempt {attempt + 1}")
                break

            except Exception as e:
                # Extract underlying error
                underlying_error = extract_exception_from_group(e)
                error_str = str(e)

                # Check if retryable
                is_taskgroup_error = "TaskGroup" in error_str or "ExceptionGroup" in error_str

                if is_taskgroup_error and attempt < max_retries - 1:
                    # Exponential backoff
                    delay = min(base_retry_delay * (2 ** attempt), max_delay)

                    print(f"[SAFE-MERGE] [WARN] MCP get_pipeline failed (attempt {attempt + 1}/{max_retries})")
                    print(f"[SAFE-MERGE] [ERROR] {underlying_error}")
                    print(f"[SAFE-MERGE] [RETRY] Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    error_msg = f"[X] MERGE BLOCKED: Failed to get pipeline after {attempt + 1} attempts: {underlying_error}"
                    print(f"[SAFE-MERGE] {error_msg}")
                    return {"error": error_msg, "blocked": True}

        pipeline_id = pipeline.get('id')
        pipeline_status = pipeline.get('status')

        # STEP 3: ENFORCE - Pipeline status must be "success"
        if pipeline_status != 'success':
            error_msg = f"[X] MERGE BLOCKED: Pipeline status is '{pipeline_status}', not 'success'"
            print(f"[SAFE-MERGE] {error_msg}")
            print(f"[SAFE-MERGE]    Pipeline ID: #{pipeline_id}")
            print(f"[SAFE-MERGE]    Branch: {source_branch}")
            return {
                "error": error_msg,
                "blocked": True,
                "pipeline_status": pipeline_status,
                "pipeline_id": pipeline_id
            }

        # STEP 4: ENFORCE - All jobs must be successful (with advanced retry logic)
        jobs_result = None

        for attempt in range(max_retries):
            try:
                # Shield from external cancellation
                jobs_result = await asyncio.shield(
                    get_jobs_tool.ainvoke({
                        "project_id": project_id,
                        "pipeline_id": pipeline_id
                    })
                )

                # Handle both list and string responses
                if isinstance(jobs_result, str):
                    import json
                    jobs = json.loads(jobs_result)
                else:
                    jobs = jobs_result

                # Success - break out of retry loop
                print(f"[SAFE-MERGE] [OK] list_pipeline_jobs succeeded on attempt {attempt + 1}")
                break

            except Exception as e:
                # Extract underlying error
                underlying_error = extract_exception_from_group(e)
                error_str = str(e)

                # Check if retryable
                is_taskgroup_error = "TaskGroup" in error_str or "ExceptionGroup" in error_str

                if is_taskgroup_error and attempt < max_retries - 1:
                    # Exponential backoff
                    delay = min(base_retry_delay * (2 ** attempt), max_delay)

                    print(f"[SAFE-MERGE] [WARN] MCP list_pipeline_jobs failed (attempt {attempt + 1}/{max_retries})")
                    print(f"[SAFE-MERGE] [ERROR] {underlying_error}")
                    print(f"[SAFE-MERGE] [RETRY] Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed
                    error_msg = f"[X] MERGE BLOCKED: Failed to get pipeline jobs after {attempt + 1} attempts: {underlying_error}"
                    print(f"[SAFE-MERGE] {error_msg}")
                    return {"error": error_msg, "blocked": True}

        failed_jobs = [j for j in jobs if j.get('status') != 'success']
        if failed_jobs:
            error_msg = f"[X] MERGE BLOCKED: {len(failed_jobs)} job(s) failed"
            print(f"[SAFE-MERGE] {error_msg}")
            for job in failed_jobs:
                print(f"[SAFE-MERGE]    - {job.get('name')}: {job.get('status')}")
            return {
                "error": error_msg,
                "blocked": True,
                "failed_jobs": [j.get('name') for j in failed_jobs]
            }

        # STEP 5: ENFORCE - MR must be mergeable
        merge_status = mr.get('merge_status')
        if merge_status != 'can_be_merged':
            error_msg = f"[X] MERGE BLOCKED: MR merge_status is '{merge_status}', not 'can_be_merged'"
            print(f"[SAFE-MERGE] {error_msg}")
            return {
                "error": error_msg,
                "blocked": True,
                "merge_status": merge_status
            }

        # STEP 6: ALL CHECKS PASSED - Allow merge
        print(f"[SAFE-MERGE] [OK] All validations passed - proceeding with merge")
        print(f"[SAFE-MERGE]    Pipeline #{pipeline_id}: {pipeline_status}")
        print(f"[SAFE-MERGE]    All {len(jobs)} jobs successful")
        print(f"[SAFE-MERGE]    MR #{mr_iid} is mergeable")

        # Call the REAL merge tool
        merge_params = {
            "project_id": project_id,
            "mr_iid": mr_iid
        }

        if merge_commit_message:
            merge_params["merge_commit_message"] = merge_commit_message

        # Add any additional kwargs
        merge_params.update(kwargs)

        result = await merge_tool.ainvoke(merge_params)

        print(f"[SAFE-MERGE] [OK] Merge completed successfully")
        return result

    # Create wrapped tool with same interface as original
    return StructuredTool.from_function(
        func=safe_merge_merge_request,
        name="merge_merge_request",
        description=(
            "Merge a merge request with optional validation. "
            "By default, AUTOMATICALLY validates pipeline success before merging. "
            "\n\nParameters:\n"
            "- project_id: GitLab project ID\n"
            "- mr_iid: Merge request IID  \n"
            "- merge_commit_message: Optional commit message\n"
            "- skip_validation: Set to True to skip validation if you've already verified:\n"
            "  1. Pipeline status is 'success'\n"
            "  2. All pipeline jobs are 'success'\n"
            "  3. MR merge_status is 'can_be_merged'\n"
            "\nUSE skip_validation=True when:\n"
            "- You've manually verified all conditions using get_merge_request, get_pipeline, list_pipeline_jobs\n"
            "- The automatic validation is failing due to MCP connection issues\n"
            "- You've confirmed the MR is ready to merge but the tool keeps failing\n"
            "\nWithout skip_validation, will return error if validation fails or pipeline is not successful."
        ),
        coroutine=safe_merge_merge_request
    )


def create_validate_merge_conditions_tool(
    get_mr_tool: StructuredTool,
    get_pipeline_tool: StructuredTool,
    get_jobs_tool: StructuredTool
) -> StructuredTool:
    """
    Create a validation-only tool that checks if an MR is ready to merge.
    This allows agents to verify conditions without actually merging.
    """

    async def validate_merge_conditions(
        project_id: str,
        mr_iid: int
    ) -> Dict[str, Any]:
        """
        Validate if an MR meets all merge conditions.

        Returns dict with 'ready' boolean and detailed status.
        """
        print(f"\n[VALIDATE-MERGE] Checking merge readiness for MR #{mr_iid}...")

        try:
            # Get MR details
            mr_result = await get_mr_tool.ainvoke({
                "project_id": project_id,
                "mr_iid": mr_iid
            })
            mr = mr_result if isinstance(mr_result, dict) else __import__('json').loads(mr_result)

            # Get pipeline
            source_branch = mr.get('source_branch')
            pipeline_result = await get_pipeline_tool.ainvoke({
                "project_id": project_id,
                "ref": source_branch
            })
            pipeline = pipeline_result if isinstance(pipeline_result, dict) else __import__('json').loads(pipeline_result)

            # Get jobs
            pipeline_id = pipeline.get('id')
            jobs_result = await get_jobs_tool.ainvoke({
                "project_id": project_id,
                "pipeline_id": pipeline_id
            })
            jobs = jobs_result if isinstance(jobs_result, list) else __import__('json').loads(jobs_result)

            # Validate conditions
            pipeline_status = pipeline.get('status')
            merge_status = mr.get('merge_status')
            failed_jobs = [j for j in jobs if j.get('status') != 'success']

            ready = (
                pipeline_status == 'success' and
                merge_status == 'can_be_merged' and
                len(failed_jobs) == 0
            )

            result = {
                "ready": ready,
                "mr_status": merge_status,
                "pipeline_status": pipeline_status,
                "pipeline_id": pipeline_id,
                "total_jobs": len(jobs),
                "failed_jobs": len(failed_jobs),
                "details": {
                    "mr_mergeable": merge_status == 'can_be_merged',
                    "pipeline_success": pipeline_status == 'success',
                    "all_jobs_success": len(failed_jobs) == 0
                }
            }

            if ready:
                print(f"[VALIDATE-MERGE] [OK] MR #{mr_iid} is READY to merge")
                print(f"[VALIDATE-MERGE]    Pipeline #{pipeline_id}: {pipeline_status}")
                print(f"[VALIDATE-MERGE]    All {len(jobs)} jobs successful")
                print(f"[VALIDATE-MERGE]    MR status: {merge_status}")
            else:
                print(f"[VALIDATE-MERGE] [X] MR #{mr_iid} is NOT ready to merge")
                if not result["details"]["mr_mergeable"]:
                    print(f"[VALIDATE-MERGE]    MR status: {merge_status} (expected: can_be_merged)")
                if not result["details"]["pipeline_success"]:
                    print(f"[VALIDATE-MERGE]    Pipeline status: {pipeline_status} (expected: success)")
                if not result["details"]["all_jobs_success"]:
                    print(f"[VALIDATE-MERGE]    Failed jobs: {len(failed_jobs)}/{len(jobs)}")

            return result

        except Exception as e:
            error = extract_exception_from_group(e)
            print(f"[VALIDATE-MERGE] [ERROR] Validation failed: {error}")
            return {
                "ready": False,
                "error": error,
                "details": {}
            }

    return StructuredTool.from_function(
        func=validate_merge_conditions,
        name="validate_merge_conditions",
        description=(
            "Validate if a merge request is ready to merge WITHOUT actually merging it. "
            "Checks:\n"
            "1. Pipeline status is 'success'\n"
            "2. All pipeline jobs are 'success'\n"
            "3. MR merge_status is 'can_be_merged'\n"
            "\nReturns dict with 'ready' boolean and detailed status.\n"
            "Use this to verify merge conditions before calling merge_merge_request with skip_validation=True."
        ),
        coroutine=validate_merge_conditions
    )


def wrap_tools_with_safety(tools: List[Any]) -> List[Any]:
    """
    Wrap dangerous tools with safety validation.

    Currently wraps:
    - merge_merge_request: Validates pipeline success before merging
    - Adds validate_merge_conditions: Check merge readiness without merging

    This function is idempotent - calling it multiple times is safe.

    Args:
        tools: List of LangChain tools from MCP

    Returns:
        List of tools with dangerous ones wrapped
    """
    # Find required tools
    merge_tool = None
    get_mr_tool = None
    get_pipeline_tool = None
    get_jobs_tool = None

    for tool in tools:
        if tool.name == 'merge_merge_request':
            merge_tool = tool
        elif tool.name == 'get_merge_request':
            get_mr_tool = tool
        elif tool.name == 'get_pipeline':
            get_pipeline_tool = tool
        elif tool.name == 'list_pipeline_jobs':
            get_jobs_tool = tool

    # Only wrap if all required tools are available
    if not all([merge_tool, get_mr_tool, get_pipeline_tool, get_jobs_tool]):
        print("[SAFE-TOOLS] Warning: Cannot create safe merge tool - missing required tools")
        return tools

    # Check if already wrapped (idempotency check)
    if hasattr(merge_tool, 'func') and 'safe_merge_merge_request' in str(merge_tool.func):
        # Already wrapped, return as-is
        return tools

    # Create safe wrapper
    safe_merge_tool = create_safe_merge_tool(
        merge_tool,
        get_mr_tool,
        get_pipeline_tool,
        get_jobs_tool
    )

    # Create validation helper tool
    validate_tool = create_validate_merge_conditions_tool(
        get_mr_tool,
        get_pipeline_tool,
        get_jobs_tool
    )

    # Replace merge tool with safe version and add validation tool
    wrapped_tools = [
        safe_merge_tool if t.name == 'merge_merge_request' else t
        for t in tools
    ]
    wrapped_tools.append(validate_tool)

    print("[SAFE-TOOLS] [OK] Wrapped merge_merge_request with validation")
    print("[SAFE-TOOLS] [OK] Added validate_merge_conditions tool")

    return wrapped_tools
