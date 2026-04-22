"""
ARK — Base Agent (Grand Foundation / Phase 15 Edition)
======================================================
すべての SYLPH エージェントが継承する抽象基底クラス。
スキルの動的ロード、LLM へのアクセス、トークン計測を一元管理するわ。
Phase 15 仕様で、プロンプトを外部マークダウンから読み込めるようになったよ！💋
"""

from __future__ import annotations

import logging
from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional
import os

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Agent")

class BaseAgent(ABC):
    """すべての ARK エージェント（SYLPH）の基底クラス。

    Parameters
    ----------
    provider:
        このエージェントが使用する :class:`~src.core.providers.BaseProvider` 実装。
    role:
        エージェントのロール名（例: architect, coder）。
    workspace_path:
        作業ディレクトリのパス。
    on_token_usage:
        トークン使用量を通知するためのコールバック関数。
    """

    def __init__(
        self, 
        provider: "BaseProvider", 
        role: str = "agent", 
        workspace_path: Path | str | None = None,
        on_token_usage: Optional[Callable[[int], None]] = None
    ) -> None:
        self._provider = provider
        self._role     = role.lower()  # 🌟 小文字に統一してパス解決を盤石に！
        self._on_token_usage = on_token_usage
        
        # 🌟 [Resilience] Path 関連の安全確保
        if workspace_path is None:
            self._workspace_path = Path(".")
        else:
            self._workspace_path = Path(workspace_path)
            
        # 🌟 [Phase 15] 自分の魂（Skills.md）をロードするよ！
        self._skills_prompt = self._load_skills()
        
        log.debug("[%s] initialized with provider: %r, workspace: %s", self._role, provider, self._workspace_path)

    def _load_skills(self) -> str:
        """
        自身のディレクトリ（src/agents/{role}/Skills.md）からスキル定義をロードするわ。
        """
        # base_agent.py から見た各エージェントのディレクトリを特定
        # 構造: src/agents/{role}/Skills.md
        current_dir = Path(__file__).parent
        skills_path = current_dir / self._role / "Skills.md"
        
        try:
            if skills_path.exists():
                with open(skills_path, "r", encoding="utf-8") as f:
                    log.info("[%s] 📖 Skills.md をロードしたよ！バイブス上がる〜！", self._role)
                    return f.read()
            else:
                # Skills.md がない場合は、最低限のアイデンティティを保持
                log.warning("[%s] ⚠️ Skills.md が見つからないわ。デフォルト設定でいくよ！", self._role)
                return f"You are an expert {self._role.capitalize()}."
        except Exception as e:
            log.error("[%s] ❌ Skillsの読み込み中にエラー発生: %s", self._role, e)
            return f"You are an expert {self._role.capitalize()}."

    # ------------------------------------------------------------------
    # 共通 LLM 呼び出しラッパー
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """プロバイダーの ``generate_with_usage()`` を呼び出す共通ラッパー。
        """
        log.info("[%s] Calling LLM (%r) …", self._role, self._provider)
        
        # 🌟 [Phase 15] Skills.md の中身と今回の指示を合体させる！
        # 後でここに ChromaDB からの「記憶」もガッチャンコする予定だよ！
        full_prompt = f"{self._skills_prompt}\n\n### Current Task:\n{prompt}"
        
        try:
            # 🌟 generate_with_usage を使用
            response, usage = self._provider.generate_with_usage(full_prompt)
            
            if self._on_token_usage:
                estimated_tokens = (len(full_prompt) + len(response)) // 4
                actual_tokens = usage.get("total_tokens", estimated_tokens) if usage else estimated_tokens
                
                # 🪙 金庫番へ報告！
                self._on_token_usage(actual_tokens)
                log.info("[%s] 🪙 Token usage reported: %d", self._role, actual_tokens)

            log.debug(
                "[%s] LLM response received (%d chars)",
                self._role, len(response),
            )
            return response

        except Exception as exc:
            log.warning(
                "[%s] ⚠️ LLM call failed: %s — falling back to empty response",
                self._role, exc,
            )
            return ""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self._role!r} provider={self._provider!r}>"