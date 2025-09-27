"""
Planning Management Module
Handles issue prioritization, dependency analysis, and planning execution.
"""

import asyncio
import re
from typing import Dict, List, Any, Optional


class PlanningManager:
    """
    Manages planning operations including prioritization and dependency analysis.
    """

    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.current_plan = None

    async def execute_planning_with_retry(self, route_task_func, apply_changes: bool) -> bool:
        """Execute planning agent with retry logic."""
        for attempt in range(self.max_retries):
            if attempt > 0:
                print(f"[RETRY] Planning attempt {attempt + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay * attempt)

            try:
                success = await route_task_func("planning", apply=apply_changes)
                if success:
                    return True
            except Exception as e:
                print(f"[PLANNING] Attempt {attempt + 1} failed: {e}")

        return False

    async def apply_planning_prioritization(
        self,
        all_issues: List[Dict[str, Any]],
        planning_result: Any,
        is_completed_func
    ) -> List[Dict[str, Any]]:
        """
        Apply planning agent's prioritization and filter out completed issues.
        """
        print("[PLANNING] Applying planning agent's prioritization...")

        # Extract prioritized issue order from planning agent's analysis
        prioritized_issues = []

        if planning_result:
            print("[PLANNING] Using planning agent's analysis for prioritization")
            # Extract issue order from planning text (if available)
            prioritized_issues = self.extract_issue_priority_from_plan(planning_result, all_issues)

        if not prioritized_issues:
            print("[PLANNING] No specific prioritization found, using dependency-based ordering")
            # Fallback: Use dependency-based prioritization
            prioritized_issues = self.apply_dependency_based_prioritization(all_issues)

        # Filter out completed/merged issues
        filtered_issues = []
        for issue in prioritized_issues:
            if await is_completed_func(issue):
                issue_id = issue.get('iid') or issue.get('id')
                print(f"[SKIP] Issue #{issue_id} already completed/merged")
                continue
            filtered_issues.append(issue)

        return filtered_issues

    def extract_issue_priority_from_plan(self, plan_data: Any, all_issues: List[Dict]) -> List[Dict]:
        """
        Extract issue priority order from planning agent's analysis.
        """
        if isinstance(plan_data, str):
            # Parse text-based plan for issue priorities
            return self.parse_text_plan_priorities(plan_data, all_issues)
        elif isinstance(plan_data, dict) and 'issues' in plan_data:
            # Use structured plan format
            return self.parse_structured_plan_priorities(plan_data, all_issues)
        else:
            return []

    def parse_text_plan_priorities(self, plan_text: str, all_issues: List[Dict]) -> List[Dict]:
        """
        Parse text-based planning output for issue priorities.
        """
        prioritized = []
        issue_map = {str(issue.get('iid')): issue for issue in all_issues}

        # Pattern 1: "Phase 1: Issues #1, #5"
        phase_pattern = r'Phase \d+.*?Issue[s]?\s*[#:]?\s*([#\d,\s]+)'
        phases = re.findall(phase_pattern, plan_text, re.IGNORECASE)

        for phase in phases:
            # Extract issue numbers from each phase
            issue_numbers = re.findall(r'#?(\d+)', phase)
            for num in issue_numbers:
                if num in issue_map and issue_map[num] not in prioritized:
                    prioritized.append(issue_map[num])

        # Pattern 2: "Issue #X" mentions in order
        if not prioritized:
            issue_mentions = re.findall(r'Issue #(\d+)', plan_text)
            for num in issue_mentions:
                if num in issue_map and issue_map[num] not in prioritized:
                    prioritized.append(issue_map[num])

        # Add any remaining issues not mentioned in the plan
        for issue in all_issues:
            if issue not in prioritized:
                prioritized.append(issue)

        return prioritized

    def parse_structured_plan_priorities(self, plan_data: Dict, all_issues: List[Dict]) -> List[Dict]:
        """
        Parse structured plan format for issue priorities.
        """
        prioritized = []
        issue_map = {str(issue.get('iid')): issue for issue in all_issues}

        if 'issues' in plan_data:
            for planned_issue in plan_data['issues']:
                issue_id = str(planned_issue.get('id') or planned_issue.get('iid', ''))
                if issue_id in issue_map:
                    prioritized.append(issue_map[issue_id])

        # Add any remaining issues
        for issue in all_issues:
            if issue not in prioritized:
                prioritized.append(issue)

        return prioritized

    def apply_dependency_based_prioritization(self, all_issues: List[Dict]) -> List[Dict]:
        """
        Apply dependency-based prioritization as fallback.
        Based on common patterns: foundation issues first, then dependent features.
        """
        foundation_keywords = ['project', 'user', 'login', 'setup', 'database', 'model']
        feature_keywords = ['task', 'display', 'overview', 'form', 'list']
        ui_keywords = ['color', 'style', 'display', 'interface', 'gui']

        foundation_issues = []
        feature_issues = []
        ui_issues = []
        other_issues = []

        for issue in all_issues:
            title = issue.get('title', '').lower()
            description = issue.get('description', '').lower()
            text = f"{title} {description}"

            if any(keyword in text for keyword in foundation_keywords):
                foundation_issues.append(issue)
            elif any(keyword in text for keyword in ui_keywords):
                ui_issues.append(issue)
            elif any(keyword in text for keyword in feature_keywords):
                feature_issues.append(issue)
            else:
                other_issues.append(issue)

        # Return in dependency order: foundation → features → UI → others
        return foundation_issues + feature_issues + other_issues + ui_issues

    def store_plan(self, plan_data: Any):
        """Store planning result for later use."""
        self.current_plan = plan_data
        if plan_data:
            print("[PLANNING] Stored planning result for issue prioritization")

    def get_current_plan(self) -> Any:
        """Get the current stored plan."""
        return self.current_plan