"""
ARK — Base Agent
================
すべてのSYLPHエージェントが継承する抽象基底クラス。

設計原則
--------
- ``BaseProvider`` をコンストラクタで受け取り（依存性注入）、LLMへのアクセスを抽象化する。
- ``_call_llm()`` 共通ラッパーを通じて、ロギングとエラーハンドリングを一元管理する。
- 各具体エージェントはシステムプロンプトを内蔵し、`generate()` を経由してPayloadを生成する。
"""

from __future__ import annotations

import logging
from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Agent")


class BaseAgent(ABC):
    """すべてのARKエージェント（SYLPH）の基底クラス。

    Parameters
    ----------
    provider:
        このエージェントが使用する :class:`~src.core.providers.BaseProvider` 実装。
        Orchestratorから依存性注入で渡される。
    role:
        エージェントのロール名。ログ出力に使用する（例: ``"architect"``）。
    """

    def __init__(self, provider: "BaseProvider", role: str = "agent", workspace_path: Path | str | None = None) -> None:
        self._provider = provider
        self._role     = role
        
        # 👇 ここが「E」の嵐を止める魔法の1行！
        # None が来たら Path(".") （カレントディレクトリ）をデフォルトにするわ
        self._workspace_path = Path(workspace_path) if workspace_path is not None else Path(".")
        
        log.debug("[%s] initialized with provider: %r, workspace: %s", self._role, provider, self._workspace_path)
    # ------------------------------------------------------------------
    # 共通LLM呼び出しラッパー
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """プロバイダーの ``generate()`` を呼び出す共通ラッパー。

        ロギングとエラーハンドリングを一元化する。

        Parameters
        ----------
        prompt:
            LLMに送信するプロンプト文字列。

        Returns
        -------
        str
            LLMが生成したテキスト応答。
            エラー時は空文字列を返し、呼び出し元でフォールバック処理を行う。
        """
        log.info("[%s] Calling LLM (%r) …", self._role, self._provider)
        try:
            response = self._provider.generate(prompt)
            log.debug(
                "[%s] LLM response received (%d chars)",
                self._role, len(response),
            )
            return response
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[%s] LLM call failed: %s — falling back to default",
                self._role, exc,
            )
            return ""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self._role!r} provider={self._provider!r}>"
