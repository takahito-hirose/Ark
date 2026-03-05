"""
ARK — Architect Agent (SYLPH)
==============================
設計フェーズを担当するエージェント。

責務
----
- ユーザーのゴールを分析し、 :class:`~src.core.models.PlanPayload` を生成する。
- LLMへのプロンプトにはシステム指示（設計ロール・出力フォーマット要件）を内蔵する。
- LLMレスポンスのパース失敗時はセーフなデフォルト値でフォールバックし、
  Orchestratorのリトライループを継続できるようにする。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path  # 👈 地味に抜けてたから足しておいたわ💋
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent
from src.core.agents import build_architect_prompt
from src.core.models import PlanPayload

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Architect")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
あなたはARKフレームワークのArchitect SYLPHです。
ユーザーのゴールを分析し、実装計画（PlanPayload）を生成してください。

## 出力フォーマット（厳守）
TARGET_FILES: <カンマ区切りのファイルパスリスト>
CONSTRAINTS: <カンマ区切りの制約リスト>
ACCEPTANCE: <カンマ区切りの受け入れ基準リスト>

## 制約
- ファイルパスは workspace/ からの相対パスで記述
- Python 3.11+ 対応コードを前提とする
- 型ヒントを必須とする
- 外部ライブラリが必要な場合は必ず TARGET_FILES に requirements.txt を含めること

## ゴール
{goal}
"""


# ---------------------------------------------------------------------------
# ArchitectAgent
# ---------------------------------------------------------------------------

class ArchitectAgent(BaseAgent):
    """設計担当SYLPHエージェント。

    LLMにゴールを渡して設計を行い、 :class:`~src.core.models.PlanPayload` を返す。

    Parameters
    ----------
    provider:
        使用する :class:`~src.core.providers.BaseProvider` 実装。
    """

    def __init__(self, provider: "BaseProvider", workspace_path: Path | None = None) -> None:
        super().__init__(provider, role="architect", workspace_path=workspace_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, goal: str, task_id: str) -> PlanPayload:
        """ゴールを分析し :class:`~src.core.models.PlanPayload` を生成する。"""
        log.info("[Architect] Analysing goal: %r", goal[:60])
        
        # 👈 ここがキモ！ ゴールに直接「鉄の掟」を強制注入！
        enhanced_goal = (
            f"{goal}\n\n"
            "【必須ルール】\n"
            "外部ライブラリ（requestsなど）を使用する場合は、必ず TARGET_FILES のリストに 'requirements.txt' を含めてください。"
        )

        # src/core/agents.py のロジックを使用してプロンプトを構築
        prompt = build_architect_prompt(enhanced_goal, self._workspace_path)
        response = self._call_llm(prompt)
        
        # payload生成時には、ログ等が汚れないように元の goal を渡すわ
        return self._parse_response(response, goal=goal, task_id=task_id)

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        response: str,
        *,
        goal: str,
        task_id: str,
    ) -> PlanPayload:
        """LLMレスポンスから :class:`~src.core.models.PlanPayload` を抽出する。

        パース失敗時はデフォルト値にフォールバックする。
        """
        default_file = f"workspace/output_{task_id[:8]}.py"

        target_files   = self._extract_list(response, "TARGET_FILES",  [default_file])
        constraints    = self._extract_list(response, "CONSTRAINTS",   ["Python 3.11+", "型ヒント必須"])
        acceptance     = self._extract_list(response, "ACCEPTANCE",    ["no syntax errors", "file exists"])

        payload = PlanPayload(
            goal=goal,
            spec_path="specs/core_logic.md",
            target_files=target_files,
            constraints=constraints,
            acceptance_criteria=acceptance,
        )
        log.info(
            "[Architect] PlanPayload created: target_files=%s",
            payload.target_files,
        )
        return payload

    @staticmethod
    def _extract_list(text: str, key: str, default: list[str]) -> list[str]:
        """``KEY: value1, value2`` 形式の行をパースしてリストを返す。"""
        pattern = rf"^{re.escape(key)}\s*:\s*(.+)$"
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if not match:
            log.debug("Key %r not found in LLM response, using default.", key)
            return default
        raw = match.group(1).strip()
        items = [item.strip() for item in raw.split(",") if item.strip()]
        return items if items else default