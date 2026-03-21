"""
ARK — Reflector Agent (SYLPH)
=============================
振り返りフェーズを担当するエージェント。

責務
----
- 完了したミッション（Goal）と最終的なコード（CodePayload）を分析する。
- 記憶ツールを自律的に使用し、将来の航海に役立つ知見（Telescopeの検索結果含む）やコアルールを永続化する。💋
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from src.agents.base_agent import BaseAgent
from src.core.agents import build_reflector_prompt # 🌟 Canvasで定義した最新のプロンプトを使用！
from src.core.models import CodePayload, PlanPayload

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Reflector")

class ReflectorAgent(BaseAgent):
    """振り返り担当SYLPHエージェント。"""

    def __init__(
        self, 
        provider: "BaseProvider", 
        workspace_path: Path | None = None,
        tools: list[Any] | None = None,
        on_token_usage: Optional[Callable[[int], None]] = None
    ) -> None:
        super().__init__(
            provider, 
            role="reflector", 
            workspace_path=workspace_path,
            on_token_usage=on_token_usage
        )
        self.workspace_path = workspace_path
        self.tools = tools or []

    def reflect(self, plan: PlanPayload, code: CodePayload) -> None:
        """ゴールとコードを分析し、記憶ツールを実行する。"""
        log.info("[Reflector] Analysing completed task for memory extraction…")

        # 🌟 PlanPayload に格納されている検索結果を安全に取り出す
        search_results = getattr(plan, "search_results", "")
        
        # 🌟 変更されたファイルのリストを作成
        files = [fc.path for fc in code.files]
        
        # 🌟 最終的に生成されたコードのサマリーを作成
        parts = []
        for fc in code.files:
            parts.append(f"### File: {fc.path}\n```python\n{fc.content}\n```")
        code_summary = "\n\n".join(parts) if parts else "(no files)"

        # 🌟 中央工場から最新のプロンプトを生成！検索結果もバケツリレーするわよ💋
        prompt = build_reflector_prompt(
            goal=plan.goal,
            files=files,
            code_summary=code_summary,
            search_results=search_results
        )
        
        response = self._call_llm(prompt)
        self._handle_tool_calls(response)

    def _handle_tool_calls(self, response: str) -> None:
        """LLMのレスポンスから TOOL_CALL コマンドを検知して直接実行する💋"""
        tool_executed = False
        for line in response.split("\n"):
            line = line.strip()
            
            # 1. 経験のアーカイブ (archive_experience)
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
                                
            # 2. コアルールの保存 (save_core_rule)
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