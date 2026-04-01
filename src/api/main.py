"""
ARK — API Server (The Neural Link)
==================================
ARKのオーケストレーターをAPIとして公開し、WebSocket経由で思考プロセスを
リアルタイムにストリーミング配信する。
(server.py と仕様を完全に同期：Treasury連携済み)
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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
        logger.info("New HUD client connected to Neuro-Link.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Client disconnected.")

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

class CommandRequest(BaseModel):
    command: str
    workspace_path: Optional[str] = None
    auto_approve_search: bool = False
    architect_provider: Optional[str] = None
    coder_provider: Optional[str] = None
    reviewer_provider: Optional[str] = None
    reflector_provider: Optional[str] = None

def create_status_callback(loop: asyncio.AbstractEventLoop):
    def callback(phase: Phase, status: str, retry_count: int, detail: str = ""):
        phase_name = phase.value if hasattr(phase, 'value') else phase
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "ARK_EVENT",
                "phase": phase_name,
                "status": status,
                "retry_count": retry_count,
                "detail": detail,
                "timestamp": loop.time()
            }),
            loop
        )
    return callback

def create_token_usage_callback(loop: asyncio.AbstractEventLoop):
    def callback(tokens_used: int, cost: float = 0.0):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "TOKEN_USAGE",
                "tokens": tokens_used,
                "cost": cost
            }),
            loop
        )
    return callback

def create_cost_update_callback(loop: asyncio.AbstractEventLoop):
    def callback(payload: dict):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(payload),
            loop
        )
    return callback

def create_proposal_callback(loop: asyncio.AbstractEventLoop):
    def callback(proposal_data: dict):
        logger.info(f"Orchestrator generated a proposal! Broadcasting to HUD.")
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "PROPOSAL_READY",
                "data": proposal_data
            }),
            loop
        )
    return callback

@app.get("/")
def read_root():
    return {"status": "ARK Online", "version": "11.2-link"}

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_ark_mission(req: CommandRequest):
    loop = asyncio.get_running_loop()
    
    config_overrides = {}
    if req.architect_provider: config_overrides["architect_provider"] = req.architect_provider
    if req.coder_provider: config_overrides["coder_provider"] = req.coder_provider
    if req.reviewer_provider: config_overrides["reviewer_provider"] = req.reviewer_provider
    if req.reflector_provider: config_overrides["reflector_provider"] = req.reflector_provider

    try:
        orc = Orchestrator(
            on_status_change=create_status_callback(loop),
            on_token_usage=create_token_usage_callback(loop),
            on_cost_update=create_cost_update_callback(loop),
            on_proposal=create_proposal_callback(loop),
            workspace_path=req.workspace_path,
            auto_approve_search=req.auto_approve_search,
            config_overrides=config_overrides
        )
        await loop.run_in_executor(None, orc.run, req.command)
    except Exception as e:
        logger.error("Orchestrator failed: %s", e)
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "ARK_EVENT",
                "phase": "BLOCKED",
                "status": "CRITICAL_ERROR",
                "detail": str(e)
            }),
            loop
        )

@app.post("/api/command")
async def execute_command(req: CommandRequest, background_tasks: BackgroundTasks):
    logger.info("Command Received from HUD: %s", req.command)
    background_tasks.add_task(run_ark_mission, req=req)
    return {"message": "Mission accepted", "level": "success"}

@app.post("/api/command/approve")
async def approve_proposal(req: CommandRequest, background_tasks: BackgroundTasks):
    logger.info("Proposal Approved by Captain! Launching new course: %s", req.command)
    background_tasks.add_task(run_ark_mission, req=req)
    return {"message": "Proposal approved and mission launched", "level": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["src"] 
    )