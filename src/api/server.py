"""
ARK — Bridge Server (The Final Fix) 🚀
=====================================
1. 通信ループの同期問題を解決
2. 余計な監視ログを抑制
3. workspace を監視から除外
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
# watchfiles と uvicorn のノイズをカット！💋
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

def run_orchestrator_sync(goal: str, mode: str, workspace_path: Optional[str], main_loop: asyncio.AbstractEventLoop):
    """メインスレッドのループを使って報告するわ！💋"""
    
    def on_status_change(phase, status, retry_count, detail=""):
        # メインループにブロードキャストを依頼する
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

    def on_token_usage(tokens):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "TOKEN_USAGE",
                "tokens": tokens
            }),
            main_loop
        )

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
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "ARK_EVENT",
                "phase": "BLOCKED",
                "status": "CRITICAL_ERROR",
                "detail": str(e)
            }),
            main_loop
        )

@app.post("/api/command")
async def handle_command(request: CommandRequest, background_tasks: BackgroundTasks):
    log.info("💬 Command Received: %s", request.command)
    
    # 現在のメインループを取得して渡す
    main_loop = asyncio.get_running_loop()
    
    background_tasks.add_task(
        run_orchestrator_sync, 
        request.command, 
        request.mode, 
        request.workspace_path,
        main_loop
    )
    return {"status": "accepted"}

if __name__ == "__main__":
    import uvicorn
    # reload=True を使うなら、reload_dirs で src だけを指すのが安全よ！
    # それでもダメなら reload=False にして手動起動が一番確実💋
    uvicorn.run(
        "src.api.server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["src"]
    )