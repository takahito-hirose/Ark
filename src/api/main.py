"""
ARK — API Server (The Neural Link)
==================================
ARKのオーケストレーターをAPIとして公開し、WebSocket経由で思考プロセスを
リアルタイムにストリーミング配信する。
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# ここで Orchestrator などのインポートが続くわ...
from src.core.orchestrator import Orchestrator, Phase

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ARK.Bridge")

app = FastAPI(title="ARK Neuro-Link API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("📡 New HUD client connected to Neuro-Link.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("📡 Client disconnected.")

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

class CommandRequest(BaseModel):
    command: str
    mode: str = "ECO"
    workspace_path: str | None = None

def create_status_callback(loop: asyncio.AbstractEventLoop):
    def callback(phase: Phase, status: str, retry_count: int, detail: str = ""):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "ARK_EVENT",
                "phase": phase.value,
                "status": status,
                "retry_count": retry_count,
                "detail": detail,
                "timestamp": loop.time()
            }),
            loop
        )
    return callback

def create_token_usage_callback(loop: asyncio.AbstractEventLoop):
    def callback(tokens_used: int):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "TOKEN_USAGE",
                "tokens": tokens_used
            }),
            loop
        )
    return callback

@app.get("/")
def read_root():
    return {"status": "ARK Online", "version": "4.5.1-dock"}

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_ark_mission(goal: str, mode: str = "ECO", workspace_path: str | None = None):
    loop = asyncio.get_running_loop()
    orc = Orchestrator(
        on_status_change=create_status_callback(loop),
        on_token_usage=create_token_usage_callback(loop),
        mode=mode,
        workspace_path=workspace_path
    )
    await loop.run_in_executor(None, orc.run, goal)

@app.post("/api/command")
async def execute_command(req: CommandRequest, background_tasks: BackgroundTasks):
    logger.info("💬 Command Received from HUD: %s", req.command)
    background_tasks.add_task(run_ark_mission, goal=req.command, mode=req.mode, workspace_path=req.workspace_path)
    return {"message": "Mission accepted", "level": "success"}

# --- ここが重要！ ---
if __name__ == "__main__":
    import uvicorn
    # reload_dirs に "src" を指定することで、
    # workspace フォルダ（仮想環境など）の変更で再起動しないようにするわ！
    uvicorn.run(
        "src.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["src"] 
    )