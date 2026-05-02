# /Users/taks/Ark/src/api/main.py

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.core.orchestrator import Orchestrator
from src.api.slack_bot import start_slack_bot, set_slack_callbacks, send_slack_message
from src.api.models import CommandRequest
from src.api.ws_manager import manager
from src.api.callbacks import (
    approval_manager,
    create_status_callback,
    create_token_usage_callback,
    create_cost_update_callback,
    create_proposal_callback,
    create_plan_ready_callback,
    create_thought_callback # 🌟 NEW: ここでインポート！
)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ARK.Bridge")

main_loop: Optional[asyncio.AbstractEventLoop] = None

class SlackPRNotificationHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            if "Pull Request が完成したわ！ URL: " in msg:
                url = msg.split("URL: ")[-1].strip()
                if main_loop and main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        send_slack_message(f"🎉 *ミッション完了！Pull Request が作成されました！*\n{url}"),
                        main_loop
                    )
        except Exception:
            pass

logging.getLogger().addHandler(SlackPRNotificationHandler())

async def handle_slack_command(command: str, auto_approve: bool, workspace_path: Optional[str] = None, providers: dict = None):
    providers = providers or {}
    logger.info(f"🚀 Launching mission from Slack: {command} (Workspace: {workspace_path}, Providers: {providers})")
    req = CommandRequest(
        command=command, 
        auto_approve_search=auto_approve, 
        workspace_path=workspace_path,
        architect_provider=providers.get("architect_provider"),
        coder_provider=providers.get("coder_provider"),
        reviewer_provider=providers.get("reviewer_provider"),
        reflector_provider=providers.get("reflector_provider")
    )
    asyncio.create_task(run_ark_mission(req))

def handle_slack_approval(approved: bool):
    logger.info(f"🚦 Slack Approval Received: {approved}")
    approval_manager.set_plan_response(approved)
    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(manager.broadcast({"type": "PLAN_APPROVED", "approved": approved}), main_loop)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    logger.info("Starting FastAPI Server and initializing Slack Neuro-Link...")
    set_slack_callbacks(handle_slack_command, handle_slack_approval)
    slack_task = asyncio.create_task(start_slack_bot())
    yield
    logger.info("Shutting down server...")
    slack_task.cancel()

app = FastAPI(title="ARK Neuro-Link API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ARK Online", "version": "16.5-bridge"}

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                if data.get("type") == "PLAN_RESPONSE":
                    approved = data.get("approved", False)
                    logger.info(f"Captain responded to PLAN: Approved={approved}")
                    approval_manager.set_plan_response(approved)
                    await manager.broadcast({"type": "PLAN_APPROVED", "approved": approved})
            except json.JSONDecodeError:
                pass
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
            on_plan_ready=create_plan_ready_callback(loop),  
            on_agent_thought=create_thought_callback(loop), # 🌟 NEW: Orchestrator に思考通信ケーブルを接続！
            workspace_path=req.workspace_path,
            auto_approve_search=req.auto_approve_search,
            config_overrides=config_overrides
        )
        await loop.run_in_executor(None, orc.run, req.command)
    except Exception as e:
        logger.error("Orchestrator failed: %s", e)
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({"type": "ARK_EVENT", "phase": "BLOCKED", "status": "CRITICAL_ERROR", "detail": str(e)}),
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