"""
ARK agents package — SYLPH (Architect, Coder, Reviewer, Reflector) logic.
Phase 15: Domain-Driven Directory Structure Edition 💋
"""

# BaseAgentは移動していないので元のパスのままでOK！
from src.agents.base_agent import BaseAgent

# 各エージェントは専用フォルダ配下の agent.py から呼び出すよ！
from src.agents.architect.agent import ArchitectAgent
from src.agents.coder.agent import CoderAgent
from src.agents.reviewer.agent import ReviewerAgent
from src.agents.reflector.agent import ReflectorAgent

__all__ = [
    "BaseAgent",
    "ArchitectAgent",
    "CoderAgent",
    "ReviewerAgent",
    "ReflectorAgent",
]