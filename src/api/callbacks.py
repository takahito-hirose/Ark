# /Users/taks/Ark/src/api/callbacks.py

import asyncio
import logging
import threading
from src.core.orchestrator import Phase
from src.api.ws_manager import manager
from src.api.slack_bot import (
    send_slack_approval_message,
    send_slack_next_proposal_message
)

logger = logging.getLogger("ARK.Bridge.Callbacks")

class ApprovalManager:
    def __init__(self):
        self.plan_event = threading.Event()
        self.is_plan_approved = False
        
        self.search_event = threading.Event()
        self.is_search_approved = False

    def wait_for_plan_approval(self) -> bool:
        self.plan_event.clear()
        self.plan_event.wait()
        return self.is_plan_approved

    def set_plan_response(self, approved: bool):
        self.is_plan_approved = approved
        self.plan_event.set()

approval_manager = ApprovalManager()

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
            manager.broadcast({"type": "TOKEN_USAGE", "tokens": tokens_used, "cost": cost}),
            loop
        )
    return callback

def create_cost_update_callback(loop: asyncio.AbstractEventLoop):
    def callback(payload: dict):
        asyncio.run_coroutine_threadsafe(manager.broadcast(payload), loop)
    return callback

def create_proposal_callback(loop: asyncio.AbstractEventLoop):
    def callback(proposal_data: dict):
        logger.info(f"Orchestrator generated a proposal! Broadcasting to HUD and Slack.")
        asyncio.run_coroutine_threadsafe(manager.broadcast({"type": "PROPOSAL_READY", "data": proposal_data}), loop)
        asyncio.run_coroutine_threadsafe(send_slack_next_proposal_message(proposal_data), loop)
    return callback

def create_plan_ready_callback(loop: asyncio.AbstractEventLoop):
    def callback(plan_data: dict) -> bool:
        logger.info("Plan ready! Broadcasting to HUD and waiting for Captain's approval...")
        asyncio.run_coroutine_threadsafe(manager.broadcast({"type": "PLAN_READY", "plan": plan_data}), loop)
        asyncio.run_coroutine_threadsafe(send_slack_approval_message(plan_data), loop)
        return approval_manager.wait_for_plan_approval()
    return callback

# 🌟 NEW: 思考（Thought）をWebSocketに流すためのコールバックを追加！
def create_thought_callback(loop: asyncio.AbstractEventLoop):
    def callback(agent_name: str, task: str, thought: str, tool_name: str = None):
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "AGENT_THOUGHT",
                "agent": agent_name,
                "task": task,
                "thought_process": thought,
                "current_tool": tool_name
            }),
            loop
        )
    return callback