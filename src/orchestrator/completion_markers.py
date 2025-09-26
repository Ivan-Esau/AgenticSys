"""
Centralized completion markers and success detection patterns.
Single source of truth for agent completion signals.
"""

from typing import Dict, List, Tuple


class CompletionMarkers:
    """Manages completion markers and success detection for all agents."""

    # Agent completion signals - these MUST match what agents output
    SIGNALS = {
        "planning": "PLANNING_PHASE_COMPLETE",
        "coding": "CODING_PHASE_COMPLETE",
        "testing": "TESTING_PHASE_COMPLETE",
        "review": "REVIEW_PHASE_COMPLETE"
    }

    # Additional success patterns for flexible detection
    SUCCESS_PATTERNS = {
        "planning": [
            "planning status: complete",
            "planning complete",
            "orchestration plan",
            "plan created",
            "planning is complete",
            "existing orchestration plan found",
            "planning analysis complete",
            "ready for implementation",
            "project analysis completed"
        ],
        "coding": [
            "implementation complete",
            "code complete",
            "files created",
            "implementation successful",
            "production code ready"
        ],
        "testing": [
            "tests complete",
            "tests pass",
            "all tests passing",
            "testing successful",
            "pipeline success confirmed"
        ],
        "review": [
            "review complete",
            "merge request created",
            "ready to merge",
            "review successful",
            "merged and closed successfully"
        ]
    }

    # Error signals to detect failures
    ERROR_SIGNALS = {
        "planning": ["PLANNING_FAILED", "planning failed"],
        "coding": ["CODING_FAILED", "CODING_RETRYING"],
        "testing": ["TESTS_FAILED", "TESTS_DEBUGGING", "TESTING_FAILED"],
        "review": ["PIPELINE_FAILED", "REVIEW_FAILED", "MERGE_BLOCKED", "PIPELINE_BLOCKED"]
    }

    # Pipeline-specific failure markers
    PIPELINE_FAILURES = {
        "tests": "PIPELINE_FAILED_TESTS",
        "build": "PIPELINE_FAILED_BUILD",
        "lint": "PIPELINE_FAILED_LINT",
        "deploy": "PIPELINE_FAILED_DEPLOY",
        "network": "PIPELINE_FAILED_NETWORK",
        "blocked": "PIPELINE_BLOCKED",
        "merge_blocked": "MERGE_BLOCKED"
    }

    @classmethod
    def check_completion(cls, agent_type: str, output: str) -> Tuple[bool, float, str]:
        """
        Check if agent output indicates successful completion.

        Args:
            agent_type: Type of agent (planning, coding, testing, review)
            output: Agent output to check

        Returns:
            Tuple of (success, confidence, reason)
        """
        if not output:
            return False, 0.0, "No output from agent"

        output_lower = output.lower()

        # Check for primary completion signal
        primary_signal = cls.SIGNALS.get(agent_type, "").lower()
        if primary_signal and primary_signal in output_lower:
            return True, 1.0, f"Found primary completion signal: {cls.SIGNALS[agent_type]}"

        # Check for error signals
        error_patterns = cls.ERROR_SIGNALS.get(agent_type, [])
        for error_pattern in error_patterns:
            if error_pattern.lower() in output_lower:
                return False, 1.0, f"Found error signal: {error_pattern}"

        # Check for secondary success patterns
        success_patterns = cls.SUCCESS_PATTERNS.get(agent_type, [])
        matches = sum(1 for pattern in success_patterns if pattern.lower() in output_lower)

        if matches > 0:
            confidence = min(1.0, matches * 0.3)
            return True, confidence, f"Found {matches} success patterns"

        return False, 0.0, "No success markers found"

    @classmethod
    def get_expected_signal(cls, agent_type: str) -> str:
        """Get the expected completion signal for an agent type."""
        return cls.SIGNALS.get(agent_type, "UNKNOWN_COMPLETION")

    @classmethod
    def format_completion_message(cls, agent_type: str, issue_id: str = None, **kwargs) -> str:
        """
        Format a proper completion message for an agent.

        Args:
            agent_type: Type of agent
            issue_id: Issue ID if available
            **kwargs: Additional context (e.g., pipeline_url)

        Returns:
            Formatted completion message
        """
        base_signal = cls.SIGNALS.get(agent_type, "COMPLETION")

        if agent_type == "planning":
            return f"{base_signal}: Planning analysis complete. Ready for implementation."

        elif agent_type == "coding":
            issue_part = f"Issue #{issue_id} " if issue_id else ""
            return f"{base_signal}: {issue_part}implementation finished. Production code ready for Testing Agent."

        elif agent_type == "testing":
            issue_part = f"Issue #{issue_id} " if issue_id else ""
            pipeline_url = kwargs.get('pipeline_url', 'N/A')
            return f"{base_signal}: {issue_part}tests finished. Pipeline success confirmed at {pipeline_url}. All tests passing for handoff to Review Agent."

        elif agent_type == "review":
            issue_part = f"Issue #{issue_id} " if issue_id else ""
            return f"{base_signal}: {issue_part}merged and closed successfully. Ready for next issue."

        return f"{base_signal}: Task completed successfully."

    @classmethod
    def has_pipeline_failure(cls, output: str) -> bool:
        """Check if output contains pipeline failure markers."""
        if not output:
            return False
        output_lower = output.lower()
        # Check for any pipeline failure marker
        for marker in cls.PIPELINE_FAILURES.values():
            if marker.lower() in output_lower:
                return True
        # Also check for generic pipeline failure patterns
        failure_patterns = [
            "pipeline failed",
            "pipeline status: failed",
            "pipeline status: canceled",
            "not merging",
            "cannot merge",
            "merge blocked"
        ]
        return any(pattern in output_lower for pattern in failure_patterns)

    @classmethod
    def get_pipeline_failure_type(cls, output: str) -> str:
        """Get the type of pipeline failure from output."""
        if not output:
            return None
        output_lower = output.lower()
        for failure_type, marker in cls.PIPELINE_FAILURES.items():
            if marker.lower() in output_lower:
                return failure_type
        return None

    @classmethod
    def should_retry_pipeline(cls, output: str) -> bool:
        """Check if pipeline should be retried due to network issues."""
        if not output:
            return False
        # Check for network-related failures that can be retried
        network_indicators = [
            "PIPELINE_FAILED_NETWORK",
            "connection timed out",
            "connection refused",
            "repo.maven.apache.org",
            "registry.npmjs.org",
            "pypi.org",
            "network error",
            "could not resolve host"
        ]
        output_lower = output.lower()
        return any(indicator.lower() in output_lower for indicator in network_indicators)

    @classmethod
    def extract_issue_number(cls, output: str) -> str:
        """Extract issue number from output text."""
        if not output:
            return None
        import re
        # Look for "Issue #123" or "issue-123" patterns
        patterns = [
            r'Issue #(\d+)',
            r'issue-(\d+)',
            r'#(\d+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        return None