"""
Clean modular BaseAgent.
Lightweight coordinator using specialized modules for caching, streaming, and tool management.
"""

from typing import Optional, List, Any, Callable, Awaitable, TypedDict
import logging
from src.core.llm.config import Config
from src.core.llm.llm_config import make_model
# Removed broken state tools and cache systems
from .core.stream_manager import StreamManager

# Configure logger for agent errors
logger = logging.getLogger(__name__)


class AgentInput(TypedDict):
    """
    TypedDict for LangGraph agent input.

    LangGraph expects a specific input format that matches TypedDict protocol.
    """
    messages: List[tuple[str, str]]


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
        project_id: Optional[str] = None,
        output_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.project_id = project_id
        self.output_callback = output_callback  # Optional WebSocket output callback

        # Initialize modular components (removed broken caching)
        self.stream_manager = StreamManager(name)
        
        # Use tools directly (no caching needed)
        agent_tools = tools
        
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
        self.agent = create_react_agent(model, agent_tools)
    
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
        # Use TypedDict to satisfy LangGraph's expected input format
        inputs: AgentInput = {"messages": [("user", full_instruction)]}

        try:
            # Try streaming first
            final_content = await self._stream_run(inputs, show_tokens)
            if final_content:
                return final_content
        except (RuntimeError, ValueError, ConnectionError) as e:
            # Stream failed, fall back to non-streaming
            logger.debug(f"[{self.name}] Streaming failed: {e}, falling back to non-streaming")
            # Continue to fallback below

        try:
            # Fallback: non-streaming execution
            if show_tokens:
                print(f"[{self.name.upper()}] Streaming failed, using non-streaming mode...")

            result = await self.agent.ainvoke(inputs, config={"recursion_limit": Config.AGENT_RECURSION_LIMIT})

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

        except (RuntimeError, ValueError, KeyError, AttributeError) as e:
            # Log specific agent execution errors
            logger.error(f"[{self.name}] Agent execution failed: {e}", exc_info=True)
            print(f"[{self.name.upper()}] [FAIL] Agent execution failed: {e}")
            return None
    
    async def _output(self, text: str, end: str = "", flush: bool = True):
        """
        Send output to WebSocket (if callback provided) or console.

        Args:
            text: Text to output
            end: String to append after text (default: empty)
            flush: Whether to flush output (default: True)
        """
        full_text = text + end

        if self.output_callback:
            # Send to WebSocket via callback
            try:
                await self.output_callback(full_text)
            except (ConnectionError, RuntimeError, OSError) as e:
                # Fall back to console if WebSocket fails
                logger.warning(f"[{self.name}] WebSocket output failed: {e}, falling back to console")
                print(full_text, end="", flush=flush)
        else:
            # Normal console output
            print(full_text, end="", flush=flush)

    async def _stream_run(self, inputs: AgentInput, show_tokens: bool) -> Optional[str]:
        """
        Run agent with streaming using efficient astream() method with stream_mode="messages".

        Args:
            inputs: TypedDict input for the agent (matches LangGraph's expected format)
            show_tokens: Whether to show token streaming

        Returns:
            Final content from streaming or None if failed

        Raises:
            RuntimeError: If streaming fails
            ValueError: If input format is invalid
            ConnectionError: If network issues occur
        """
        # ✅ FIXED: Use astream() with stream_mode="messages" for sentence-level streaming
        # Accumulate tokens into sentences for better readability
        final_content = []
        sentence_buffer = []  # Buffer tokens until we hit sentence boundary

        async for token, metadata in self.agent.astream(
            inputs,
            config={"recursion_limit": Config.AGENT_RECURSION_LIMIT},
            stream_mode="messages"  # Stream LLM tokens as they're generated
        ):
            # Extract content from token
            content = None
            if hasattr(token, "content"):
                content = token.content
            elif isinstance(token, dict) and "content" in token:
                content = token["content"]

            if content:
                content_str = str(content)
                sentence_buffer.append(content_str)
                final_content.append(content_str)

                # Send when we hit sentence boundaries or get enough tokens
                # Sentence boundaries: . ! ? followed by space, or newline
                should_send = (
                    content_str.endswith('. ') or
                    content_str.endswith('.\n') or
                    content_str.endswith('! ') or
                    content_str.endswith('?\n') or
                    content_str.endswith('? ') or
                    '\n' in content_str or
                    len(sentence_buffer) >= 15  # Send every ~15 tokens as fallback
                )

                if should_send and show_tokens:
                    # Send accumulated sentence
                    sentence = "".join(sentence_buffer)
                    await self._output(sentence)
                    sentence_buffer = []  # Reset buffer

        # Send any remaining content
        if show_tokens and sentence_buffer:
            await self._output("".join(sentence_buffer))

        # Add final newline
        if show_tokens and final_content:
            await self._output("\n")

        # Return accumulated content
        return "".join(final_content) if final_content else None
    
    def get_agent_info(self) -> dict:
        """Get basic agent information."""
        return {
            "name": self.name,
            "project_id": self.project_id
        }