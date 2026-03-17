"""
ARK — API Server (The Neural Link)
==================================
ARKのオーケストレーターをAPIとして公開し、WebSocket経由で思考プロセスを
リアルタイムにストリーミング配信する。
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from src.core.orchestrator import Orchestrator, Phase

# .env の読み込み
load_dotenv()

# ロギング設定 💋
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ARK.API")

app = FastAPI(title="ARK Neuro-Link API")

# CORS設定（Phase 5のフロントエンドと通信するために必要よ！）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 接続中のクライアントを管理するマネージャー
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("📡 New client connected to Neuro-Link.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("📡 Client disconnected.")

    async def broadcast(self, message: Dict[str, Any]):
        """全クライアントにARKの思考（脳波）を送信！💋"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# リクエストのモデル
class MissionRequest(BaseModel):
    goal: str

# 🌟 NEW: フロントエンドのターミナルからの入力用モデル！
class CommandRequest(BaseModel):
    command: str
    mode: str = "ECO"  # デフォルトは無料の ECO にしておくわ💋

# ARKのイベントをWebSocketに中継するコールバック関数
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
    """ARKの思考ログをリアルタイム配信するエンドポイント 💋"""
    await manager.connect(websocket)
    try:
        while True:
            # クライアントからのメッセージ待機（生存確認）
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 🌟 FIX: 重複していた関数定義を整理し、run_in_executor のエラーを修正！
async def run_ark_mission(goal: str, mode: str = "ECO"):
    """裏側でARKの自律ループを走らせるわ！🚀"""
    loop = asyncio.get_running_loop()
    
    # API経由でOrchestratorを起動
    orc = Orchestrator(
        on_status_change=create_status_callback(loop),
        on_token_usage=create_token_usage_callback(loop),
        mode=mode  # 🌟 FIX: 受け取った mode を確実にセット！
    )
    
    # 別のスレッドで実行（Orchestratorがブロッキング処理のため）
    # 👇 FIX: run_in_executor はキーワード引数を直接受け取れないので、余計なおまけを削除！
    await loop.run_in_executor(None, orc.run, goal)

@app.post("/mission")
async def start_mission(request: MissionRequest, background_tasks: BackgroundTasks):
    """新しいミッション（造船命令）を受付！🛳️"""
    logger.info(f"📥 New Mission Received: {request.goal}")
    background_tasks.add_task(run_ark_mission, goal=request.goal)
    return {"message": "Mission accepted. ARK is calculating the course...", "goal": request.goal}

# 🌟 NEW: フロントのホログラムHUD（コマンド入力）と繋ぐためのAPI！
@app.post("/api/command")
async def execute_command(req: CommandRequest, background_tasks: BackgroundTasks):
    """HUDターミナルからの指示を受け取って、本物のARKを起動するエンドポイント 💋"""
    # 👇 ここで受け取ったモードをログに出して確認！
    logger.info("💬 Command Received from HUD: %s (Mode: %s)", req.command, req.mode)
    
    # 🌟 FIX: 位置引数ではなく、キーワード引数で確実に mode をバケツリレーするわよ！
    background_tasks.add_task(run_ark_mission, goal=req.command, mode=req.mode)
    
    return {
        "message": f"Mission accepted! ARK is navigating: \'{req.command}\'",
        "level": "success"
    }

if __name__ == "__main__":
    import uvicorn
    # `src.api.main:app` にすることで、ホットリロードが効くようになるよ！
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)