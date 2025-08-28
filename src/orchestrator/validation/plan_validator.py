"""
Plan validation logic for the supervisor orchestrator.
Validates plan structure and integrity.
"""

from typing import Dict, Any, List, Optional


class PlanValidator:
    """
    Validates plan structure and integrity.
    Pure validation logic without state dependencies.
    """
    
    @staticmethod
    def validate_plan_structure(plan: Dict[str, Any]) -> bool:
        """
        Validate the structure of a generated plan.
        
        Args:
            plan: Plan dictionary to validate
            
        Returns:
            bool: True if plan structure is valid, False otherwise
        """
        if not isinstance(plan, dict):
            print("[VALIDATION] ❌ Plan must be a dictionary")
            return False
        
        # Check required top-level fields
        required_fields = ["issues", "implementation_order"]
        for field in required_fields:
            if field not in plan:
                print(f"[VALIDATION] ❌ Plan missing required field: {field}")
                return False
        
        # Validate issues structure
        if not PlanValidator._validate_plan_issues(plan.get("issues", [])):
            return False
        
        # Validate implementation order
        if not PlanValidator._validate_implementation_order(
            plan.get("implementation_order", []), 
            plan.get("issues", [])
        ):
            return False
        
        return True
    
    @staticmethod
    def _validate_plan_issues(issues: Any) -> bool:
        """Validate the issues section of a plan."""
        if not isinstance(issues, list):
            print("[VALIDATION] ❌ Plan issues must be a list")
            return False
        
        if not issues:
            print("[VALIDATION] ⚠️ Plan contains no issues")
            return True  # Empty is valid, just unusual
        
        seen_iids = set()
        for idx, issue in enumerate(issues):
            if not isinstance(issue, dict):
                print(f"[VALIDATION] ❌ Plan issue {idx} must be a dictionary")
                return False
            
            # Check required fields
            if "iid" not in issue:
                print(f"[VALIDATION] ❌ Plan issue {idx} missing required field: iid")
                return False
            
            # Check for duplicate IIDs
            iid = str(issue["iid"])
            if iid in seen_iids:
                print(f"[VALIDATION] ❌ Duplicate issue ID in plan: {iid}")
                return False
            seen_iids.add(iid)
            
            # Validate optional fields if present
            if "dependencies" in issue:
                if not isinstance(issue["dependencies"], list):
                    print(f"[VALIDATION] ❌ Issue {iid} dependencies must be a list")
                    return False
        
        return True
    
    @staticmethod
    def _validate_implementation_order(order: Any, issues: List[Dict]) -> bool:
        """Validate the implementation order matches available issues."""
        if not isinstance(order, list):
            print("[VALIDATION] ❌ Implementation order must be a list")
            return False
        
        # Get all issue IDs from issues list
        issue_ids = {str(issue["iid"]) for issue in issues if isinstance(issue, dict) and "iid" in issue}
        order_ids = {str(iid) for iid in order}
        
        # Check that all order IDs exist in issues
        missing_in_issues = order_ids - issue_ids
        if missing_in_issues:
            print(f"[VALIDATION] ❌ Implementation order contains IDs not in issues: {missing_in_issues}")
            return False
        
        # Check that all issue IDs are in order (unless optional)
        missing_in_order = issue_ids - order_ids
        if missing_in_order:
            print(f"[VALIDATION] ⚠️ Issues not in implementation order: {missing_in_order}")
            # This is a warning, not an error - some issues might be optional
        
        return True
    
    @staticmethod
    def validate_plan_consistency(plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate plan consistency and return detailed report.
        
        Args:
            plan: Plan to validate
            
        Returns:
            Dict containing validation results and details
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {}
        }
        
        try:
            if not isinstance(plan, dict):
                result["valid"] = False
                result["errors"].append("Plan must be a dictionary")
                return result
            
            # Basic structure validation
            if not PlanValidator.validate_plan_structure(plan):
                result["valid"] = False
                result["errors"].append("Plan structure validation failed")
                return result
            
            # Collect statistics
            issues = plan.get("issues", [])
            result["stats"]["total_issues"] = len(issues)
            result["stats"]["issues_with_dependencies"] = sum(
                1 for issue in issues 
                if issue.get("dependencies") and len(issue["dependencies"]) > 0
            )
            
            # Validate dependency consistency
            dependency_errors = PlanValidator._validate_dependency_consistency(issues)
            if dependency_errors:
                result["errors"].extend(dependency_errors)
                result["valid"] = False
            
            # Check for circular dependencies
            circular_deps = PlanValidator._check_circular_dependencies(issues)
            if circular_deps:
                result["errors"].extend([f"Circular dependency detected: {dep}" for dep in circular_deps])
                result["valid"] = False
            
        except Exception as e:
            result["valid"] = False
            result["errors"].append(f"Validation exception: {e}")
        
        return result
    
    @staticmethod
    def _validate_dependency_consistency(issues: List[Dict]) -> List[str]:
        """Check that all dependencies reference valid issues."""
        errors = []
        issue_ids = {str(issue["iid"]) for issue in issues if "iid" in issue}
        
        for issue in issues:
            if "dependencies" not in issue:
                continue
                
            issue_id = str(issue["iid"])
            for dep_id in issue["dependencies"]:
                dep_id_str = str(dep_id)
                if dep_id_str not in issue_ids:
                    errors.append(f"Issue {issue_id} depends on non-existent issue {dep_id_str}")
        
        return errors
    
    @staticmethod
    def _check_circular_dependencies(issues: List[Dict]) -> List[str]:
        """Check for circular dependencies in the plan."""
        # Build dependency graph
        deps = {}
        for issue in issues:
            if "iid" not in issue:
                continue
            issue_id = str(issue["iid"])
            deps[issue_id] = [str(dep) for dep in issue.get("dependencies", [])]
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []
        
        def has_cycle(node: str, path: List[str]) -> bool:
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(" → ".join(path[cycle_start:] + [node]))
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in deps.get(node, []):
                if has_cycle(neighbor, path + [node]):
                    return True
            
            rec_stack.remove(node)
            return False
        
        # Check each node
        for issue_id in deps:
            if issue_id not in visited:
                has_cycle(issue_id, [])
        
        return cycles