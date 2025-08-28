"""
Clean modular BaseAgent.
Lightweight coordinator using specialized modules for caching, streaming, and tool management.
"""

from typing import Optional, List, Any
from src.core.llm.config import Config
from src.core.llm.llm_config import make_model
from src.core.context.state import get_project_state, ProjectState
from .core.cache_manager import CacheManager
from .core.stream_manager import StreamManager
from .core.tool_wrapper import ToolWrapper

# LangGraph for agent creation
from langgraph.prebuilt import create_react_agent


class BaseAgent:
    """
    Clean modular base agent using specialized components.
    Coordinates caching, streaming, and tool management through dedicated modules.
    """
    
    def __init__(
        self, 
        name: str, 
        system_prompt: str, 
        tools: List[Any], 
        model=None, 
        project_id: Optional[str] = None
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.project_id = project_id
        
        # Get project state for caching and coordination
        self.state = get_project_state(project_id) if project_id else None
        
        # Initialize modular components
        self.cache_manager = CacheManager(self.state)
        self.stream_manager = StreamManager(name)
        self.tool_wrapper = ToolWrapper(self.cache_manager)
        
        # Wrap tools with caching capability
        wrapped_tools = self.tool_wrapper.wrap_tools_with_cache(tools)
        
        # Create LLM model
        if model is None:
            model = make_model(
                model=Config.LLM_MODEL,
                temperature=Config.LLM_TEMPERATURE,
                max_retries=Config.LLM_MAX_RETRIES,
                provider=Config.LLM_PROVIDER
            )
        
        # Create the LangGraph ReAct agent
        # Use system_prompt as the state modifier in agent creation
        from langgraph.prebuilt.chat_agent_executor import create_react_agent
        self.agent = create_react_agent(model, wrapped_tools)
    
    async def run(self, user_instruction: str, show_tokens: bool = True) -> Optional[str]:
        """
        Run the agent with modular streaming and fallback handling.
        
        Args:
            user_instruction: Instruction for the agent
            show_tokens: Whether to show token streaming
            
        Returns:
            Agent response or None if failed
        """
        # Show agent header
        self.stream_manager.show_agent_header(show_tokens)
        
        # Prepare inputs with system prompt included
        full_instruction = f"{self.system_prompt}\n\nUser Request:\n{user_instruction}"
        inputs = {"messages": [("user", full_instruction)]}
        
        try:
            # Try streaming first
            final_content = await self._stream_run(inputs, show_tokens)
            if final_content:
                return final_content
        except Exception:
            # Stream failed, fall back to non-streaming
            pass
        
        try:
            # Fallback: non-streaming execution
            if show_tokens:
                print(f"[{self.name.upper()}] Streaming failed, using non-streaming mode...")
            
            result = await self.agent.ainvoke(inputs)
            
            # Extract content from result
            if isinstance(result, dict) and "messages" in result:
                messages = result["messages"]
                if messages and len(messages) > 0:
                    last_message = messages[-1]
                    if hasattr(last_message, "content"):
                        return last_message.content
                    elif isinstance(last_message, dict) and "content" in last_message:
                        return last_message["content"]
            
            return str(result) if result else None
            
        except Exception as e:
            print(f"[{self.name.upper()}] ❌ Agent execution failed: {e}")
            return None
    
    async def _stream_run(self, inputs: dict, show_tokens: bool) -> Optional[str]:
        """
        Run agent with streaming using the stream manager.
        
        Args:
            inputs: Input dictionary for the agent
            show_tokens: Whether to show token streaming
            
        Returns:
            Final content from streaming or None if failed
        """
        try:
            # Create async stream
            stream = self.agent.astream_events(inputs, version="v2")
            
            # Handle stream events using stream manager
            final_content = await self.stream_manager.handle_stream_events(stream, show_tokens)
            
            return final_content
            
        except Exception:
            # Let the caller handle fallback
            raise
    
    def get_cache_stats(self) -> dict:
        """Get caching statistics from cache manager."""
        return self.cache_manager.get_cache_stats()
    
    def get_state_summary(self) -> dict:
        """Get state summary if available."""
        if self.state:
            return self.state.get_summary()
        return {"project_id": self.project_id, "state": "not_available"}