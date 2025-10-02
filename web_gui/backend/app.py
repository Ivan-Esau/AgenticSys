"""
FastAPI application for AgenticSys Web GUI
Clean, modular architecture with WebSocket support
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
import asyncio
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .api.routes import router
from .core.websocket import ConnectionManager
from .core.orchestrator import SystemOrchestrator

# Initialize FastAPI app
app = FastAPI(
    title="AgenticSys Web GUI",
    description="Web interface for autonomous multi-agent system",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
ws_manager = ConnectionManager()
orchestrator = SystemOrchestrator(ws_manager)

# Include API routes (with fallback handling)
try:
    print("[DEBUG] Loading API routes...")
    app.include_router(router, prefix="/api")
    print(f"[DEBUG] Routes loaded: {[route.path for route in router.routes]}")
    print(f"[DEBUG] Total routes: {len(router.routes)}")
except Exception as e:
    print(f"[ERROR] Failed to load routes: {e}")
    import traceback
    traceback.print_exc()

# Add LLM endpoints directly to ensure they're available
@app.get("/api/llm/providers")
async def get_llm_providers():
    """Get available LLM providers"""
    print("[DEBUG] LLM providers endpoint called")
    return {
        "providers": ["deepseek", "openai", "ollama"],
        "default": "deepseek"
    }

@app.get("/api/llm/models/{provider}")
async def get_llm_models(provider: str):
    """Get available models for a specific provider"""
    print(f"[DEBUG] LLM models endpoint called for provider: {provider}")
    fallback_models = {
        "deepseek": {"deepseek-chat": "DeepSeek Chat", "deepseek-coder": "DeepSeek Coder"},
        "openai": {"gpt-4": "GPT-4", "gpt-3.5-turbo": "GPT-3.5 Turbo"},
        "ollama": {"llama2": "Llama 2", "codellama": "Code Llama"}
    }
    return {
        "models": fallback_models.get(provider, {}),
        "default": list(fallback_models.get(provider, {}).keys())[0] if fallback_models.get(provider) else None
    }

@app.get("/api/llm/current")
async def get_current_llm_config():
    """Get current LLM configuration"""
    print("[DEBUG] Current LLM config endpoint called")
    import os
    return {
        "provider": os.getenv("LLM_PROVIDER", "deepseek").lower(),
        "model": os.getenv("LLM_MODEL", "deepseek-chat"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7"))
    }

# Serve static files
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Root endpoint - serve the frontend
@app.get("/")
async def root():
    """Serve the main application"""
    index_path = frontend_path / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {"message": "AgenticSys Web GUI API", "status": "running"}

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await ws_manager.connect(websocket)

    # Send current system state immediately after connection (state restoration)
    try:
        status = orchestrator.get_status()
        await websocket.send_json({
            "type": "system_status",
            "data": status,
            "timestamp": datetime.now().isoformat()
        })
        print(f"[WS] Sent current system status to new connection: running={status.get('running', False)}")
    except Exception as e:
        print(f"[WS] Failed to send initial status: {e}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle different message types
            if message["type"] == "ping":
                await websocket.send_json({"type": "pong"})

            elif message["type"] == "start_system":
                # Start the orchestrator
                config = message.get("data", {}).get("config", {})
                print(f"[DEBUG] WebSocket received config: {config}")
                await orchestrator.start(config)

            elif message["type"] == "stop_system":
                # Stop the orchestrator
                await orchestrator.stop()

            elif message["type"] == "get_status":
                # Send current status
                status = orchestrator.get_status()
                await websocket.send_json({
                    "type": "status_update",
                    "data": status
                })

    except WebSocketDisconnect as e:
        print(f"[WS] Client disconnected: {e}")
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS ERROR] Unhandled exception in WebSocket handler: {e}")
        import traceback
        traceback.print_exc()
        ws_manager.disconnect(websocket)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "orchestrator": orchestrator.get_status(),
        "websocket_clients": ws_manager.active_connections_count()
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("[STARTUP] AgenticSys Web GUI starting...")
    print("[STARTUP] WebSocket server ready")
    print("[STARTUP] API endpoints ready")
    print("[STARTUP] System initialized")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    print("[SHUTDOWN] Shutting down AgenticSys Web GUI...")
    await orchestrator.cleanup()
    await ws_manager.disconnect_all()