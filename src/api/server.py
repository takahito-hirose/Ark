"""
ARK — Bridge Server (The Final Fix)
=====================================
Phase 11.2: Treasury WebSocket Integration
1. モード(ECO/RICH)の概念を完全に撤廃。
2. UIからの動的なプロバイダー/モデル指定を受け入れ。
3. 自動承認(auto_approve_search)フラグの導入。
4. [REFACTOR] ハッキーなコスト計算を削除し、Orchestratorの `on_cost_update` に完全委譲。
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# パス解決
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.core.orchestrator import Orchestrator

load_dotenv()

# --- 🤫 ログを静かにさせる設定 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
log = logging.getLogger("ARK.Bridge")

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
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info("📡 New HUD client connected.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info("📡 HUD client disconnected.")

    async def broadcast(self, message: dict):
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

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

def run_orchestrator_sync(request: CommandRequest, main_loop: asyncio.AbstractEventLoop):
    """メインスレッドのループを使って報告するわ！💋"""
    
    def on_status_change(phase, status, retry_count, detail=""):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "ARK_EVENT",
                "phase": phase.value if hasattr(phase, 'value') else phase,
                "status": status,
                "retry_count": retry_count,
                "detail": detail
            }),
            main_loop
        )

    def on_token_usage(tokens, cost: float = 0.0):
        # 🌟 純粋なトークン消費イベント（コスト計算はTreasuryに委譲済み）
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "TOKEN_USAGE",
                "tokens": tokens,
                "cost": cost
            }),
            main_loop
        )

    def on_cost_update(payload: dict):
        # 🌟 NEW: Treasuryからの詳細なコスト情報をUIへ横流しする！
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(payload),
            main_loop
        )

    config_overrides = {}
    if request.architect_provider: config_overrides["architect_provider"] = request.architect_provider
    if request.coder_provider: config_overrides["coder_provider"] = request.coder_provider
    if request.reviewer_provider: config_overrides["reviewer_provider"] = request.reviewer_provider
    if request.reflector_provider: config_overrides["reflector_provider"] = request.reflector_provider

    try:
        log.info("🚢 Mission Launch: %s", request.command)
        orc = Orchestrator(
            workspace_path=request.workspace_path,
            on_status_change=on_status_change,
            on_token_usage=on_token_usage,
            on_cost_update=on_cost_update,  # 🌟 コールバックを接続
            auto_approve_search=request.auto_approve_search,
            config_overrides=config_overrides
        )
        
        orc.run(request.command)
        log.info("🏁 Mission Accomplished.")
        
    except Exception as e:
        log.error("❌ Orchestrator failed: %s", e)
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "ARK_EVENT",
                "phase": "BLOCKED",
                "status": "CRITICAL_ERROR",
                "detail": str(e)
            }),
            main_loop
        )