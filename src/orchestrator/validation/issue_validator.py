"""
Issue validation logic for the supervisor orchestrator.
Validates issue structure and dependencies.
"""

from typing import Dict, Any, List, Optional


class IssueValidator:
    """
    Validates issue structure and dependencies.
    Pure validation logic without state dependencies.
    """
    
    @staticmethod
    def validate_issue_structure(issue: Dict[str, Any]) -> bool:
        """
        Validate that an issue has the required structure.
        
        Args:
            issue: Issue dictionary to validate
            
        Returns:
            bool: True if issue structure is valid, False otherwise
        """
        if not isinstance(issue, dict):
            print("[VALIDATION] ❌ Issue must be a dictionary")
            return False
        
        required_fields = ["iid", "title"]
        for field in required_fields:
            if field not in issue:
                print(f"[VALIDATION] ❌ Issue missing required field: {field}")
                return False
        
        # Validate field types
        if not isinstance(issue.get("iid"), (str, int)):
            print(f"[VALIDATION] ❌ Issue iid must be string or int, got: {type(issue.get('iid'))}")
            return False
            
        if not isinstance(issue.get("title"), str):
            print(f"[VALIDATION] ❌ Issue title must be string, got: {type(issue.get('title'))}")
            return False
        
        return True
    
    @staticmethod
    def validate_issue_dependencies(
        issue: Dict[str, Any], 
        plan: Optional[Dict[str, Any]] = None,
        issue_status: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Validate that issue dependencies have been completed.
        
        Args:
            issue: Issue to validate
            plan: Implementation plan containing dependency information
            issue_status: Current status of all issues
            
        Returns:
            bool: True if dependencies are met, False otherwise
        """
        if not plan:
            return True  # No plan means no dependencies to check
        
        if not issue_status:
            issue_status = {}
        
        # Find this issue in the plan
        issue_id = str(issue["iid"])
        plan_issue = None
        for planned_issue in plan.get("issues", []):
            if str(planned_issue.get("iid")) == issue_id:
                plan_issue = planned_issue
                break
        
        if not plan_issue:
            return True  # Issue not in plan, assume no dependencies
        
        # Check if dependencies are completed
        dependencies = plan_issue.get("dependencies", [])
        for dep_id in dependencies:
            dep_status = issue_status.get(str(dep_id))
            if dep_status != "complete":
                print(f"[VALIDATION] ❌ Issue #{issue_id} dependency #{dep_id} not complete (status: {dep_status})")
                return False
        
        return True
    
    @staticmethod
    def validate_issues_batch(issues: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Validate a batch of issues.
        
        Args:
            issues: List of issues to validate
            
        Returns:
            Dict mapping issue IDs to validation results
        """
        results = {}
        
        if not isinstance(issues, list):
            print("[VALIDATION] ❌ Issues must be provided as a list")
            return results
        
        for issue in issues:
            if not isinstance(issue, dict):
                continue
                
            issue_id = str(issue.get("iid", "unknown"))
            results[issue_id] = IssueValidator.validate_issue_structure(issue)
        
        return results
    
    @staticmethod
    def get_valid_issue_states() -> List[str]:
        """Get list of valid issue states."""
        return ["pending", "in_progress", "complete", "failed"]
    
    @staticmethod
    def validate_issue_state(state: str) -> bool:
        """Validate that issue state is valid."""
        valid_states = IssueValidator.get_valid_issue_states()
        if state not in valid_states:
            print(f"[VALIDATION] ❌ Invalid issue state: {state}. Valid states: {valid_states}")
            return False
        return True
    
    @staticmethod
    def should_implement_issue(issue_id: str, issue_status: Dict[str, str]) -> bool:
        """
        Check if an issue needs implementation based on its current status.
        
        Args:
            issue_id: ID of the issue
            issue_status: Current status mapping
            
        Returns:
            bool: True if issue should be implemented, False otherwise
        """
        status = issue_status.get(str(issue_id), "pending")
        implementable_states = ["pending", "in_progress", "failed"]
        return status in implementable_states