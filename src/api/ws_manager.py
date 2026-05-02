import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("ARK.Bridge.WS")

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

    # 🌟 NEW: エージェントの思考をフロントに流し込む専用メソッド
    async def broadcast_agent_thought(self, agent_name: str, task: str, thought: str, tool_name: str = None):
        """エージェントの独り言を構造化して送信する"""
        await self.broadcast({
            "type": "AGENT_THOUGHT",
            "agent": agent_name,
            "task": task,
            "thought_process": thought,
            "current_tool": tool_name
        })

# グローバルに使えるようにインスタンス化しておくね！
manager = ConnectionManager()