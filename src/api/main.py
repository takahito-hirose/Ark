"""
ARK — API Server (The Neural Link)
==================================
ARKのオーケストレーターをAPIとして公開し、WebSocket経由で思考プロセスを
リアルタイムにストリーミング配信する。
(Phase 11.5: TDD Plan Approval & WebSocket Interactive Loop)
"""

import asyncio
import json
import logging
import os
import threading
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

# 🌟 NEW: 承認イベントの信号機！Orchestratorのスレッドをこれで一時停止させる
class ApprovalManager:
    def __init__(self):
        self.plan_event = threading.Event()
        self.is_plan_approved = False
        
        self.search_event = threading.Event()
        self.is_search_approved = False

    def wait_for_plan_approval(self) -> bool:
        self.plan_event.clear()  # 信号を赤にする
        self.plan_event.wait()   # 青になるまでここで待機！
        return self.is_plan_approved

    def set_plan_response(self, approved: bool):
        self.is_plan_approved = approved
        self.plan_event.set()    # 信号を青にする！

approval_manager = ApprovalManager()

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

# 🌟 NEW: 設計とテストの承認をフロントに投げ、返事を待機するコールバック
def create_plan_ready_callback(loop: asyncio.AbstractEventLoop):
    def callback(plan_data: dict) -> bool:
        logger.info("Plan ready! Broadcasting to HUD and waiting for Captain's approval...")
        # 1. フロントにプランのデータを送信
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "PLAN_READY",
                "plan": plan_data
            }),
            loop
        )
        # 2. 信号機を使って、フロントからの返事が来るまで Orchestrator を待機させる
        return approval_manager.wait_for_plan_approval()
    return callback

@app.get("/")
def read_root():
    return {"status": "ARK Online", "version": "11.5-link"}

# 🌟 UPDATE: フロントからの WebSocket メッセージを解析して信号機を操作する
@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                
                # プラン（テストと設計）の返答を受信！
                if data.get("type") == "PLAN_RESPONSE":
                    approved = data.get("approved", False)
                    logger.info(f"Captain responded to PLAN: Approved={approved}")
                    approval_manager.set_plan_response(approved)
                    
                # 将来用のリサーチ承認の返答
                elif data.get("type") == "SEARCH_RESPONSE":
                    approved = data.get("approved", False)
                    logger.info(f"Captain responded to SEARCH: Approved={approved}")
                    # 今後、Architectのリサーチ承認用信号機を動かすならここ！
                    
            except json.JSONDecodeError:
                pass # JSON以外は無視
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
            on_plan_ready=create_plan_ready_callback(loop),  # 🌟 NEW: 待機用コールバックを接続！
            workspace_path=req.workspace_path,
            auto_approve_search=req.auto_approve_search,
            config_overrides=config_overrides
        )
        # Orchestratorは別スレッドで走る（だから threading.Event が効く！）
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