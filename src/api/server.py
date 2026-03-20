"""
ARK — Bridge Server (FastAPI)
=============================
フロントエンド HUD からの指令を受け取り、オーケストレーターに繋ぐブリッジ。
"""

import sys
import os
from pathlib import Path

# 🌟 Pythonパスの強制解決：ここがポイントよ！💋
# src/api/server.py の親の親 (つまりプロジェクトルート) をパスに追加するわ。
# これにより、どのディレクトリから実行しても 'src.core...' がインポート可能になるの。
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 🚀 パスを解決した後にインポート！
try:
    from src.core.orchestrator import Orchestrator
except ImportError as e:
    # デバッグ用にパスを表示するわ
    print(f"DEBUG: Current sys.path: {sys.path}")
    print(f"DEBUG: Project root resolved as: {project_root}")
    raise e

# 環境変数のロード
load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ARK.Bridge")

app = FastAPI(title="ARK Neuro-Link API")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 接続管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info("📡 New HUD client connected to Neuro-Link.")

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
    mode: str = "ECO"
    workspace_path: Optional[str] = None

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        log.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

def run_orchestrator_sync(goal: str, mode: str, workspace_path: Optional[str]):
    """バックグラウンドスレッドでオーケストレーターを実行💋"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def on_status_change(phase, status, retry_count, detail=""):
        loop.run_until_complete(manager.broadcast({
            "type": "ARK_EVENT",
            "phase": phase.value if hasattr(phase, 'value') else phase,
            "status": status,
            "retry_count": retry_count,
            "detail": detail
        }))

    def on_token_usage(tokens):
        loop.run_until_complete(manager.broadcast({
            "type": "TOKEN_USAGE",
            "tokens": tokens
        }))

    try:
        log.info("🚢 Mission Launch: %s", goal)
        orc = Orchestrator(
            workspace_path=workspace_path,
            on_status_change=on_status_change,
            on_token_usage=on_token_usage,
            mode=mode
        )
        orc.run(goal)
        log.info("🏁 Mission Accomplished.")
    except Exception as e:
        log.error("❌ Orchestrator failed: %s", e)
        loop.run_until_complete(manager.broadcast({
            "type": "ARK_EVENT",
            "phase": "BLOCKED",
            "status": "CRITICAL_ERROR",
            "detail": str(e)
        }))
    finally:
        loop.close()

@app.post("/api/command")
async def handle_command(request: CommandRequest, background_tasks: BackgroundTasks):
    if request.workspace_path:
        path = Path(request.workspace_path).resolve()
        if not path.exists():
            log.warning("🚫 Target path not found: %s", request.workspace_path)
            raise HTTPException(status_code=400, detail=f"Target path does not exist: {request.workspace_path}")
        log.info("🔌 Mounting existing project at: %s", path)

    background_tasks.add_task(
        run_orchestrator_sync, 
        request.command, 
        request.mode, 
        request.workspace_path
    )
    return {"status": "accepted", "message": "Mission accepted."}

# 🛠 起動方法のガイド:
# 1. 直接実行 (パス解決あり): python src/api/server.py
# 2. Uvicornコマンド (開発用・リロードあり): uvicorn src.api.server:app --reload
if __name__ == "__main__":
    import uvicorn
    log.info("🧠 ARK Bridge Server starting on http://0.0.0.0:8000")
    # reload=True を追加したから、以前のコマンドと同じ感覚で開発できるわよ！
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)