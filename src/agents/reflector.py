"""
ARK — Reflector Agent (SYLPH)
=============================
振り返りフェーズを担当するエージェント。

責務
----
- 完了したミッション（Goal）と最終的なコード（CodePayload）を分析する。
- 記憶ツールを自律的に使用し、将来の航海に役立つ知見やコアルールを永続化する。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.agents.base_agent import BaseAgent
from src.core.models import CodePayload, PlanPayload

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Reflector")

_SYSTEM_PROMPT = """\
あなたはARKフレームワークのReflector（振り返り担当）SYLPHです。
ミッションが完了した直後に行動し、今回の経験から「将来役立つ知見」や「今後も守るべきプロジェクトのルール」を抽出し、記憶システムに保存するのがあなたの唯一の責務です。

## 記憶ツールの使用方法（厳守）
記憶ツールを使用する場合は、レスポンスの中に以下の正確なテキストフォーマットで出力してください。

1. プロジェクトの新しい「掟」や「前提ルール」を永続化する場合:
TOOL_CALL: save_core_rule | ルール名 | ルールの内容

2. 今回のタスクで得られた「成功体験」や「エラー解決の知見」をアーカイブする場合:
TOOL_CALL: archive_experience | 解決した問題や得られた知見の要約

## 振り返り対象
ミッションのゴール: {goal}
最終コードのファイル数: {file_count}

## 思考プロセス
1. ゴールを振り返り、ユーザーが「これをルールにして」と指定していたか確認する。
2. 最終コードから、工夫した点や学んだことを抽出する。
3. 必要な TOOL_CALL を出力する（複数可）。特にルール指定があった場合は必ず `save_core_rule` を実行すること。
"""

class ReflectorAgent(BaseAgent):
    """振り返り担当SYLPHエージェント。"""

    def __init__(
        self, 
        provider: "BaseProvider", 
        workspace_path: Path | None = None,
        tools: list[Any] | None = None
    ) -> None:
        super().__init__(provider, role="reflector", workspace_path=workspace_path)
        self.tools = tools or []

    def reflect(self, plan: PlanPayload, code: CodePayload) -> None:
        """ゴールとコードを分析し、記憶ツールを実行する。"""
        log.info("[Reflector] Analysing completed task for memory extraction…")

        prompt = _SYSTEM_PROMPT.format(
            goal=plan.goal,
            file_count=len(code.files)
        )
        
        response = self._call_llm(prompt)
        self._handle_tool_calls(response)

    def _handle_tool_calls(self, response: str) -> None:
        """LLMのレスポンスから TOOL_CALL コマンドを検知して直接実行する💋"""
        tool_executed = False
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("TOOL_CALL: archive_experience"):
                parts = line.split("|", 1)
                if len(parts) == 2:
                    summary = parts[1].strip()
                    for t in self.tools:
                        if t.__name__ == "archive_experience":
                            log.info(f"🧠 [振り返り] アーカイブを実行します: {summary}")
                            try:
                                t(summary)
                                tool_executed = True
                            except Exception as e:
                                log.error(f"Tool execution failed: {e}")
                                
            elif line.startswith("TOOL_CALL: save_core_rule"):
                parts = line.split("|", 2)
                if len(parts) == 3:
                    key = parts[1].strip()
                    val = parts[2].strip()
                    for t in self.tools:
                        if t.__name__ == "save_core_rule":
                            log.info(f"🧠 [振り返り] コアルールを保存します: {key} = {val}")
                            try:
                                t(key, val)
                                tool_executed = True
                            except Exception as e:
                                log.error(f"Tool execution failed: {e}")
                                
        if not tool_executed:
            log.info("[Reflector] No memories to archive this time.")