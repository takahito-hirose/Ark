"""
ARK — Base Agent (Grand Foundation)
====================================
すべての SYLPH エージェントが継承する抽象基底クラス。
LLM へのアクセス、ロギング、トークン使用量の計測を一元管理する「方舟の背骨」よ💋
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
        エージェントのロール名。
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
        self._role     = role
        self._on_token_usage = on_token_usage
        
        # 🌟 [Resilience] None の場合はカレントディレクトリをデフォルトに。
        # これで Path 関連の TypeError ("E" の嵐) を鉄壁ガードするわ！💋
        if workspace_path is None:
            self._workspace_path = Path(".")
        else:
            self._workspace_path = Path(workspace_path)
        
        log.debug("[%s] initialized with provider: %r, workspace: %s", self._role, provider, self._workspace_path)

    # ------------------------------------------------------------------
    # 共通 LLM 呼び出しラッパー
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """プロバイダーの ``generate_with_usage()`` を呼び出す共通ラッパー。

        ロギング、エラーハンドリング、そして『金庫（Treasury）』への
        トークン使用量報告を自動で行うわ。

        Parameters
        ----------
        prompt:
            LLM に送信する指示（プロンプト）。

        Returns
        -------
        str:
            LLM からの応答テキスト。
        """
        log.info("[%s] Calling LLM (%r) …", self._role, self._provider)
        try:
            # 🌟 generate_with_usage を使うことで、応答と同時に「代金（トークン）」を把握！
            response, usage = self._provider.generate_with_usage(prompt)
            
            if self._on_token_usage:
                # 使用量データがない場合のフォールバック（文字数ベースの概算）
                estimated_tokens = (len(prompt) + len(response)) // 4
                actual_tokens = usage.get("total_tokens", estimated_tokens) if usage else estimated_tokens
                
                # 🪙 金庫番（Orchestrator/UI）へ報告！
                self._on_token_usage(actual_tokens)
                log.info("[%s] 🪙 Token usage reported: %d", self._role, actual_tokens)

            log.debug(
                "[%s] LLM response received (%d chars)",
                self._role, len(response),
            )
            return response

        except Exception as exc:
            # ⚓️ ここで力尽きても、ARK は沈まない！
            log.warning(
                "[%s] ⚠️ LLM call failed: %s — falling back to empty response",
                self._role, exc,
            )
            return ""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self._role!r} provider={self._provider!r}>"