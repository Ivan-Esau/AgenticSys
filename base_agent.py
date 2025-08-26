import os
import json
import re
import asyncio
from textwrap import dedent
from dotenv import load_dotenv

# DeepSeek via LangChain (supports streaming)
from langchain_deepseek.chat_models import ChatDeepSeek
# MCP -> LangChain tools
from langchain_mcp_adapters.client import MultiServerMCPClient
# Prebuilt ReAct agent (autonomous tool use)
from langgraph.prebuilt import create_react_agent

# For robust fallback on stream errors
try:
    import httpx, httpcore
except Exception:  # libraries are present via deps in your venv, but guard anyway
    httpx = None
    httpcore = None

def _short(obj, lim: int = 240) -> str:
    try:
        s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    s = s.replace("\n", " ")
    return s[:lim] + ("…" if len(s) > lim else "")

def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.getenv(name, default)
    if required and (val is None or str(val).strip() == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return val

# --- JSON extraction for plan handoff ---------------------------------------------------------
JSON_BLOCK_RE = re.compile(r"```json(?:\s+PLAN)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
def extract_json_block(text: str) -> dict | None:
    if not text:
        return None
    m = JSON_BLOCK_RE.search(text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None

# --- MCP + model wiring ----------------------------------------------------------------------
async def load_mcp_tools():
    host = env("MCP_HOST", "localhost")
    port = env("MCP_PORT", "3333")
    path = env("MCP_PATH", "/mcp")  # adapter accepts with or without trailing slash
    url = f"http://{host}:{port}{path}"

    client = MultiServerMCPClient({
        "gitlab": {"url": url, "transport": "streamable_http"}
    })
    tools = await client.get_tools(server_name="gitlab")
    if not tools:
        raise RuntimeError("No MCP tools discovered from 'gitlab'. Check server and credentials.")
    return tools, client

def make_model():
    """
    DeepSeek chat model (LangChain integration).
    Notes:
    - DeepSeek is OpenAI-compatible; streaming uses SSE/chunked transfer.
    - If DEEPSEEK_API_BASE is set, ensure it includes '/v1' per docs.
    """
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    temperature = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2"))
    # You can tune retries/timeouts via envs:
    max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
    # stream_usage=True adds a usage summary at the end of stream
    return ChatDeepSeek(model=model, temperature=temperature, stream_usage=True, max_retries=max_retries)

class BaseAgent:
    """
    Thin wrapper that:
      - builds a LangGraph ReAct agent with a system prompt
      - streams with astream_events(v2) and prints progress (tools + tokens)
      - auto-falls-back to a non-streamed .ainvoke() if the streaming path fails
    """
    def __init__(self, name: str, system_prompt: str, tools):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.model = make_model()
        self.agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            prompt=self.system_prompt,
            name=name,
            version="v2",
        )

    async def _stream_run(self, inputs, show_tokens: bool):
        final = None
        async for ev in self.agent.astream_events(inputs, version="v2"):
            etype = ev.get("event")
            name = ev.get("name")
            data = ev.get("data", {})

            # Graph progress
            if etype == "on_chain_start" and name:
                print(f"🧭 start: {name}")
            if etype == "on_chain_end" and name:
                out = data.get("output")
                if out and isinstance(out, dict) and "messages" in out:
                    final = out
                print(f"🏁 end:   {name}")

            # Tools
            if etype == "on_tool_start" and name:
                print(f"🔧 tool → {name} args={_short(data.get('input', {}))}")
            if etype == "on_tool_end" and name:
                print(f"✅ done ← {name} result={_short(data.get('output'))}")

            # Tokens
            if show_tokens and etype == "on_chat_model_stream":
                chunk = data.get("chunk")
                text = getattr(chunk, "content", None)
                if text:
                    print(text, end="", flush=True)
            if show_tokens and etype == "on_chat_model_end":
                print()
        return final

    async def run(self, user_instruction: str, show_tokens: bool = True) -> str | None:
        inputs = {"messages": [("user", user_instruction.strip())]}
        print(f"\n=== {self.name}: live run ===")

        disable_stream = os.getenv("ORCH_DISABLE_STREAM", "").lower() in ("1", "true", "yes")
        try_stream = not disable_stream

        # 1) Preferred path: stream with live progress
        if try_stream:
            try:
                final = await self._stream_run(inputs, show_tokens=show_tokens)
                if final and "messages" in final and final["messages"]:
                    last = final["messages"][-1]
                    return getattr(last, "content", last.get("content") if isinstance(last, dict) else None)
                # If we reached here with no final message, fall through to non-stream invoke.
                print("ℹ️ streaming finished without a final message; retrying with non-stream invoke…")
            except Exception as e:
                # Known transient class of errors on SSE/chunked streaming:
                # - httpx.RemoteProtocolError / httpcore.RemoteProtocolError
                # - Connection resets / premature close
                if httpx and isinstance(e, httpx.RemoteProtocolError) or (httpcore and isinstance(e, httpcore.RemoteProtocolError)):
                    print("\n⚠️  streaming error detected (chunked/SSE broke). Falling back to non-streaming invoke.")
                else:
                    print(f"\n⚠️  streaming failed: {e}. Falling back to non-streaming invoke.")

        # 2) Robust fallback: non-streaming single-shot
        result = await self.agent.ainvoke(inputs)
        msgs = result.get("messages", [])
        if msgs:
            last = msgs[-1]
            return getattr(last, "content", last.get("content") if isinstance(last, dict) else None)
        return None

async def get_common_tools_and_client():
    load_dotenv(override=False)
    tools, client = await load_mcp_tools()
    return tools, client
