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
                issue_iid = issue.get('iid') or issue.get('id')
                print(f"[SKIP] Issue #{issue_iid} already completed/merged")
                continue
            filtered_issues.append(issue)

        return filtered_issues

    def extract_issue_priority_from_plan(self, plan_data: Any, all_issues: List[Dict]) -> List[Dict]:
        """
        Extract issue priority order from planning agent's analysis.
        Priority: ORCH_PLAN.json > text patterns > dependency-based fallback
        """
        # First, check if plan_data contains ORCH_PLAN.json structure
        if isinstance(plan_data, dict) and 'implementation_order' in plan_data:
            # ORCH_PLAN.json format - use implementation_order directly
            print("[PLANNING] Found ORCH_PLAN.json with implementation_order")
            return self.parse_implementation_order(plan_data, all_issues)

        if isinstance(plan_data, str):
            # Check if text contains ORCH_PLAN.json content
            import json
            import re
            json_match = re.search(r'\{[^{]*"implementation_order"[^}]*\}', plan_data, re.DOTALL)
            if json_match:
                try:
                    plan_json = json.loads(json_match.group())
                    if 'implementation_order' in plan_json:
                        print("[PLANNING] Extracted ORCH_PLAN.json from text")
                        return self.parse_implementation_order(plan_json, all_issues)
                except json.JSONDecodeError:
                    pass

            # Parse text-based plan for issue priorities
            return self.parse_text_plan_priorities(plan_data, all_issues)
        elif isinstance(plan_data, dict) and 'issues' in plan_data:
            # Use structured plan format
            return self.parse_structured_plan_priorities(plan_data, all_issues)
        else:
            return []

    def parse_implementation_order(self, plan_data: Dict, all_issues: List[Dict]) -> List[Dict]:
        """Parse implementation_order from ORCH_PLAN.json"""
        prioritized = []
        issue_map = {issue.get('iid'): issue for issue in all_issues}

        implementation_order = plan_data.get('implementation_order', [])
        print(f"[PLANNING] Implementation order from plan: {implementation_order}")

        for issue_iid in implementation_order:
            if issue_iid in issue_map:
                prioritized.append(issue_map[issue_iid])
                print(f"[PLANNING] Added Issue #{issue_iid} from implementation_order")

        # Add any remaining issues not in the order
        for issue in all_issues:
            if issue not in prioritized:
                prioritized.append(issue)
                print(f"[PLANNING] Added remaining Issue #{issue.get('iid')}")

        return prioritized

    def parse_text_plan_priorities(self, plan_text: str, all_issues: List[Dict]) -> List[Dict]:
        """
        Parse text-based planning output for issue priorities.
        """
        prioritized = []
        issue_map = {str(issue.get('iid')): issue for issue in all_issues}

        # Pattern 0: "ISSUE PRIORITIZATION:" section (NEW - highest priority)
        prioritization_match = re.search(
            r'ISSUE PRIORITIZATION:.*?(?:\n\d+\..*?Issue \d+.*?)+',
            plan_text,
            re.IGNORECASE | re.DOTALL
        )

        if prioritization_match:
            print("[PLANNING] Found ISSUE PRIORITIZATION section")
            prioritization_section = prioritization_match.group()
            # Extract lines like "1. Issue 1 - Project creation"
            priority_lines = re.findall(r'\d+\.\s+Issue (\d+)', prioritization_section)

            for num in priority_lines:
                if num in issue_map:
                    prioritized.append(issue_map[num])
                    print(f"[PLANNING] Priority order: Issue #{num}")

            if prioritized:
                print(f"[PLANNING] Extracted {len(prioritized)} issues from priority section")

        # Pattern 1: "Phase 1: Issues #1, #5"
        if not prioritized:
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
                issue_iid = str(planned_issue.get('id') or planned_issue.get('iid', ''))
                if issue_iid in issue_map:
                    prioritized.append(issue_map[issue_iid])

        # Add any remaining issues
        for issue in all_issues:
            if issue not in prioritized:
                prioritized.append(issue)

        return prioritized

    def apply_dependency_based_prioritization(self, all_issues: List[Dict]) -> List[Dict]:
        """
        Apply dependency-based prioritization as fallback.
        Extracts dependencies from issue descriptions ("Voraussetzungen:" section).
        """
        print("[PLANNING] Using dependency-based prioritization (parsing Voraussetzungen)")

        # Build dependency map from issue descriptions
        dependency_map = {}
        issue_map = {issue.get('iid'): issue for issue in all_issues}

        for issue in all_issues:
            issue_iid = issue.get('iid')
            description = issue.get('description', '')
            deps = self.extract_dependencies_from_description(description, issue_iid)
            dependency_map[issue_iid] = deps

        # Topological sort to get implementation order
        implementation_order = self.topological_sort(dependency_map, list(issue_map.keys()))

        # Return issues in dependency order
        prioritized = []
        for issue_iid in implementation_order:
            if issue_iid in issue_map:
                prioritized.append(issue_map[issue_iid])

        return prioritized

    def extract_dependencies_from_description(self, description: str, issue_iid: int) -> List[int]:
        """
        Extract dependencies from issue description.
        Looks for "Voraussetzungen:" or "Prerequisites:" sections.
        """
        dependencies = []

        # Pattern for Voraussetzungen/Prerequisites section
        prereq_patterns = [
            r'Voraussetzungen:?\s*(.+?)(?:\n\n|\n[A-Z]|$)',  # German
            r'Prerequisites:?\s*(.+?)(?:\n\n|\n[A-Z]|$)'      # English
        ]

        for pattern in prereq_patterns:
            match = re.search(pattern, description, re.IGNORECASE | re.DOTALL)
            if match:
                prereq_text = match.group(1).lower()
                print(f"[PLANNING] Issue #{issue_iid} prerequisites: {prereq_text[:100]}")

                # Parse dependency keywords
                if 'keine' in prereq_text or 'none' in prereq_text:
                    # No dependencies
                    print(f"[PLANNING] Issue #{issue_iid}: No dependencies (foundational)")
                    break

                # Map German dependency keywords to issue types
                keyword_to_issue = {
                    'projekt': 1,  # "Projekt existiert" → Issue 1
                    'aufgabe': 3,  # "Aufgabe existiert" → Issue 3
                    'benutzer': 5,  # "Benutzer" → Issue 5
                    'task': 3,
                    'user': 5,
                    'project': 1
                }

                for keyword, dep_issue in keyword_to_issue.items():
                    if keyword in prereq_text and dep_issue != issue_iid:
                        dependencies.append(dep_issue)

                # Extract explicit issue references (#1, Issue 2, etc.)
                explicit_refs = re.findall(r'(?:issue|aufgabe|#)\s*(\d+)', prereq_text, re.IGNORECASE)
                for ref in explicit_refs:
                    dep_issue = int(ref)
                    if dep_issue != issue_iid and dep_issue not in dependencies:
                        dependencies.append(dep_issue)

                break

        if dependencies:
            print(f"[PLANNING] Issue #{issue_iid} depends on: {dependencies}")

        return dependencies

    def topological_sort(self, dependency_map: Dict[int, List[int]], all_issue_iids: List[int]) -> List[int]:
        """
        Topological sort to order issues by dependencies.
        Issues with no dependencies come first.
        """
        # Build in-degree map (count of dependencies)
        in_degree = {iid: 0 for iid in all_issue_iids}
        for iid, deps in dependency_map.items():
            for dep in deps:
                if dep in in_degree:  # Only count dependencies that exist
                    in_degree[iid] += 1

        # Start with issues that have no dependencies
        queue = [iid for iid in all_issue_iids if in_degree[iid] == 0]
        sorted_order = []

        while queue:
            # Sort queue to ensure consistent ordering (lower IIDs first)
            queue.sort()
            current = queue.pop(0)
            sorted_order.append(current)

            # Find issues that depend on current issue
            for iid in all_issue_iids:
                if iid in dependency_map and current in dependency_map[iid]:
                    in_degree[iid] -= 1
                    if in_degree[iid] == 0 and iid not in queue:
                        queue.append(iid)

        # Add any remaining issues (circular dependencies)
        for iid in all_issue_iids:
            if iid not in sorted_order:
                sorted_order.append(iid)

        print(f"[PLANNING] Dependency-based order: {sorted_order}")
        return sorted_order

    def OLD_apply_dependency_based_prioritization(self, all_issues: List[Dict]) -> List[Dict]:
        """
        OLD: Apply dependency-based prioritization as fallback.
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

    async def load_plan_from_repository(self, mcp_client, project_id: str, ref: str = "master") -> bool:
        """
        Load ORCH_PLAN.json from the repository after planning branch is merged.

        Args:
            mcp_client: MCP client for GitLab API calls
            project_id: GitLab project ID
            ref: Branch/ref to load from (default: master)

        Returns:
            bool: True if plan was loaded successfully, False otherwise
        """
        try:
            print(f"[PLANNING] Loading ORCH_PLAN.json from {ref} branch...")

            # Try to get ORCH_PLAN.json from docs/ directory
            result = await mcp_client.run_tool("get_file_contents", {
                "project_id": str(project_id),
                "file_path": "docs/ORCH_PLAN.json",
                "ref": ref
            })

            if result and isinstance(result, str):
                import json
                try:
                    plan_json = json.loads(result)

                    # Validate it has the required structure
                    if 'implementation_order' in plan_json:
                        self.current_plan = plan_json
                        print(f"[PLANNING] ✅ Loaded ORCH_PLAN.json with {len(plan_json.get('implementation_order', []))} issues")
                        print(f"[PLANNING] Implementation order: {plan_json.get('implementation_order', [])}")
                        return True
                    else:
                        print("[PLANNING] ⚠️ ORCH_PLAN.json missing 'implementation_order' field")
                        return False

                except json.JSONDecodeError as e:
                    print(f"[PLANNING] ⚠️ Failed to parse ORCH_PLAN.json: {e}")
                    return False
            else:
                print("[PLANNING] ⚠️ ORCH_PLAN.json not found in repository")
                return False

        except Exception as e:
            print(f"[PLANNING] ⚠️ Error loading ORCH_PLAN.json: {e}")
            return False