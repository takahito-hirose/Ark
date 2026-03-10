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

# ARKのイベントをWebSocketに中継するコールバック関数
def create_status_callback(loop: asyncio.AbstractEventLoop):
    def callback(phase: Phase, status: str, retry_count: int, detail: str = ""):
        # 💡 ここ！asyncio.get_event_loop() を使わずに、
        # 引数で受け取っている 'loop' を直接使うように修正するわ💋
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "ARK_EVENT",
                "phase": phase.value,
                "status": status,
                "retry_count": retry_count,
                "detail": detail,
                "timestamp": loop.time() # 👈 get_event_loop() を削ったわ！
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

async def run_ark_mission(goal: str):
    """裏側でARKの自律ループを走らせるわ！🚀"""
    loop = asyncio.get_running_loop()
    
    # API経由でOrchestratorを起動
    # ※ status_callback を使って WebSocket に情報を飛ばす仕組みよ
    orc = Orchestrator(
        on_status_change=create_status_callback(loop)
    )
    
    # 別のスレッドで実行（Orchestratorがブロッキング処理のため）
    await loop.run_in_executor(None, orc.run, goal)

@app.post("/mission")
async def start_mission(request: MissionRequest, background_tasks: BackgroundTasks):
    """新しいミッション（造船命令）を受付！🛳️"""
    logger.info(f"📥 New Mission Received: {request.goal}")
    background_tasks.add_task(run_ark_mission, request.goal)
    return {"message": "Mission accepted. ARK is calculating the course...", "goal": request.goal}

if __name__ == "__main__":
    import uvicorn
    # サーバーを起動！
    uvicorn.run(app, host="0.0.0.0", port=8000)