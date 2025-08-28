"""
Task validation logic for the supervisor orchestrator.
Validates task prerequisites before execution.
"""

from typing import Dict, Any, Optional, List


class TaskValidator:
    """
    Validates task prerequisites and conditions before execution.
    Pure validation logic without state dependencies.
    """
    
    @staticmethod
    def validate_task_prerequisites(task_type: str, tools: Any = None, client: Any = None, **kwargs) -> bool:
        """
        Validate prerequisites for a task before execution.
        
        Args:
            task_type: Type of task to validate
            tools: Available tools
            client: MCP client
            **kwargs: Additional task-specific parameters
            
        Returns:
            bool: True if prerequisites are met, False otherwise
        """
        try:
            if task_type == "planning":
                return TaskValidator._validate_planning_prerequisites(tools, client)
                
            elif task_type == "coding":
                return TaskValidator._validate_coding_prerequisites(kwargs)
                
            elif task_type == "testing":
                return TaskValidator._validate_testing_prerequisites(tools)
                
            elif task_type == "review":
                return TaskValidator._validate_review_prerequisites(kwargs)
                
            return True
            
        except Exception as e:
            print(f"[VALIDATION] ⚠️ Validation error for {task_type}: {e}")
            return False
    
    @staticmethod
    def _validate_planning_prerequisites(tools: Any, client: Any) -> bool:
        """Validate prerequisites for planning phase."""
        if not tools:
            print("[VALIDATION] ❌ No tools available for planning")
            return False
        if not client:
            print("[VALIDATION] ❌ No MCP client available for planning")
            return False
        return True
    
    @staticmethod
    def _validate_coding_prerequisites(kwargs: Dict[str, Any]) -> bool:
        """Validate prerequisites for coding phase."""
        issue = kwargs.get("issue")
        fix_mode = kwargs.get("fix_mode", False)
        
        if issue and not fix_mode:
            # For regular coding, need valid issue
            if not issue.get("iid"):
                print("[VALIDATION] ❌ Coding task missing valid issue ID")
                return False
        
        return True  # Fix mode doesn't need issue validation
    
    @staticmethod
    def _validate_testing_prerequisites(tools: Any) -> bool:
        """Validate prerequisites for testing phase."""
        # Testing can work with or without specific issue
        if not tools:
            print("[VALIDATION] ❌ No tools available for testing")
            return False
        return True
    
    @staticmethod
    def _validate_review_prerequisites(kwargs: Dict[str, Any]) -> bool:
        """Validate prerequisites for review phase."""
        issue = kwargs.get("issue")
        branch = kwargs.get("branch")
        
        if not issue:
            print("[VALIDATION] ❌ Review task missing issue")
            return False
            
        if not branch:
            print("[VALIDATION] ❌ Review task missing branch")
            return False
            
        if not issue.get("iid"):
            print("[VALIDATION] ❌ Review task missing valid issue ID")
            return False
            
        return True
    
    @staticmethod
    def get_valid_task_types() -> List[str]:
        """Get list of valid task types."""
        return ["planning", "coding", "testing", "review"]
    
    @staticmethod
    def validate_task_type(task_type: str) -> bool:
        """Validate that task type is supported."""
        valid_types = TaskValidator.get_valid_task_types()
        if task_type not in valid_types:
            print(f"[VALIDATION] ❌ Unknown task type: {task_type}. Valid types: {valid_types}")
            return False
        return True