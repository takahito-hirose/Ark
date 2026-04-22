"""
ARK — Base Agent (Grand Foundation / Phase 15 Edition)
======================================================
すべての SYLPH エージェントが継承する抽象基底クラス。
スキルの動的ロード、自律記憶の引き出し（Dynamic RAG）、LLM 呼び出しを管理。
"""

from __future__ import annotations

import logging
from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional
import os

if TYPE_CHECKING:
    from src.core.providers import BaseProvider
    from src.memory.memory_manager import MemoryManager # 🌟 型チェック用

log = logging.getLogger("ARK.Agent")

class BaseAgent(ABC):
    def __init__(
        self, 
        provider: "BaseProvider", 
        role: str = "agent", 
        workspace_path: Path | str | None = None,
        on_token_usage: Optional[Callable[[int], None]] = None,
        memory_manager: Optional["MemoryManager"] = None # 🌟 記憶の番人を追加
    ) -> None:
        self._provider = provider
        self._role     = role.lower()
        self._on_token_usage = on_token_usage
        self._memory = memory_manager # 🌟 記憶へのアクセス権を確保
        
        if workspace_path is None:
            self._workspace_path = Path(".")
        else:
            self._workspace_path = Path(workspace_path)
            
        self._skills_prompt = self._load_skills()
        
        log.debug("[%s] initialized with memory_manager: %s", self._role, "Ready" if self._memory else "None")

    def _load_skills(self) -> str:
        """ディレクトリから Skills.md をロード（変更なし）"""
        current_dir = Path(__file__).parent
        skills_path = current_dir / self._role / "Skills.md"
        
        try:
            if skills_path.exists():
                with open(skills_path, "r", encoding="utf-8") as f:
                    log.info("[%s] 📖 Skills.md をロードしたわ！", self._role)
                    return f.read()
            else:
                log.warning("[%s] ⚠️ Skills.md がないわ。デフォルト人格でいくわよ！", self._role)
                return f"You are an expert {self._role.capitalize()}."
        except Exception as e:
            log.error("[%s] ❌ Skillsの読み込みエラー: {e}", self._role)
            return f"You are an expert {self._role.capitalize()}."

    # ------------------------------------------------------------------
    # 共通 LLM 呼び出しラッパー (Dynamic RAG 搭載)
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """
        プロバイダーを呼び出す前に、自律的に過去の「教訓」を思い出すわ💋
        """
        log.info("[%s] Calling LLM (%r) …", self._role, self._provider)
        
        # 🌟 [Phase 15 Step 3] 自分の役割に関連する記憶だけを引き出す
        relevant_memories = ""
        if self._memory:
            log.info("[%s] 🧠 過去の教訓をアーカイブから検索中...", self._role)
            # 現在のタスク(prompt)をクエリにして、自分のロールに絞って検索
            relevant_memories = self._memory.recall_memory(prompt, role=self._role, n_results=3)
            
            if relevant_memories:
                log.info("[%s] 💡 関連する記憶が見つかったわ！プロンプトに注入するわね💋", self._role)

        # 🌟 プロンプトの3層合体（人格 + 経験 + タスク）
        full_prompt = f"{self._skills_prompt}\n{relevant_memories}\n\n### Current Task:\n{prompt}"
        
        try:
            response, usage = self._provider.generate_with_usage(full_prompt)
            
            if self._on_token_usage:
                estimated_tokens = (len(full_prompt) + len(response)) // 4
                actual_tokens = usage.get("total_tokens", estimated_tokens) if usage else estimated_tokens
                self._on_token_usage(actual_tokens)

            return response

        except Exception as exc:
            log.warning("[%s] ⚠️ LLM call failed: %s", self._role, exc)
            return ""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self._role!r} provider={self._provider!r}>"