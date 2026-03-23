"""
ARK — Reflector Agent (SYLPH)
=============================
振り返りフェーズと、記憶のガベージコレクション（大掃除）を担当するエージェント。

責務
----
- 完了したミッション（Goal）と最終的なコード（CodePayload）を分析する。
- 記憶ツールを自律的に使用し、将来の航海に役立つ知見やコアルールを永続化する。
- 🧹 [NEW] 乱雑になった記憶を読み込み、自律的に整理整頓（GC）を行う司書モード💋
- 🧠 [NEW] 苦労の履歴（attempt_history）と失敗フラグ（is_failure）から、アンチパターンを学習する！
"""

from __future__ import annotations

import logging
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, Dict

from src.agents.base_agent import BaseAgent
from src.core.agents import build_reflector_prompt, build_gc_prompt # 🌟 プロンプト工場から取得！
from src.core.models import CodePayload, PlanPayload, ExecutionAttempt # 🌟 ExecutionAttempt を追加！

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Reflector")

class ReflectorAgent(BaseAgent):
    """振り返り＆記憶整理担当SYLPHエージェント。"""

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

    def reflect(
        self, 
        plan: PlanPayload, 
        code: CodePayload, 
        attempt_history: list[ExecutionAttempt] | None = None, # 🌟 Orchestratorから苦労履歴を受け取る！
        is_failure: bool = False # 🌟 Orchestratorから致命的敗北フラグを受け取る！
    ) -> None:
        """ゴールとコード、そして苦労の軌跡を分析し、記憶ツールを実行する。"""
        
        # モードに応じたログの切り替え
        if is_failure:
            log.warning("⚠️ [Reflector] 致命的な敗北を検知！アンチパターンの抽出と地雷マップの作成に移行します💋")
        else:
            log.info("✨ [Reflector] ミッション完了！成功の軌跡から知見を抽出します...")

        search_results = getattr(plan, "search_results", "")
        files = [fc.path for fc in code.files]
        
        parts = []
        for fc in code.files:
            parts.append(f"### File: {fc.path}\n```python\n{fc.content}\n```")
        code_summary = "\n\n".join(parts) if parts else "(no files)"

        # =========================================================================
        # 🌟 [PHASE 10-3 STEP 1] 苦労履歴のフォーマット化 💋
        # =========================================================================
        history_str = ""
        if attempt_history:
            log.info(f"🧠 [Reflector] {len(attempt_history)}回のトライ＆エラー履歴を分析対象に追加します。")
            h_parts = []
            for h in attempt_history:
                h_parts.append(f"--- Attempt {h.attempt_number} ---\n[Error Log]\n{h.error}")
            history_str = "\n".join(h_parts)
        else:
            if is_failure:
                history_str = "No specific error logs, but the mission failed fundamentally. (Logic/Review Error)"
            else:
                history_str = "No execution errors. The plan succeeded on the first try. Perfect!💋"
        # =========================================================================

        # 🌟 プロンプト工場に history_str と is_failure フラグを渡す！
        prompt = build_reflector_prompt(
            goal=plan.goal,
            files=files,
            code_summary=code_summary,
            search_results=search_results,
            attempt_history_str=history_str,
            is_failure=is_failure # 👈 ここが追加ポイントよ💋
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

    # =========================================================================
    # 🧹 [PHASE 10-2] ガベージコレクション（大図書館の司書モード）💋
    # =========================================================================

    def garbage_collect(self, current_memory_dump: str) -> Optional[Dict[str, Any]]:
        """
        現在の記憶ダンプを読み込み、重複や矛盾を排除して整理したJSONを返すわ💋
        """
        log.info("🧹 [Reflector] 司書モード起動！記憶の整理整頓を開始します...")

        gc_prompt = build_gc_prompt(current_memory_dump)
        response = self._call_llm(gc_prompt)
        
        # 🛡️ LLMがおしゃべりしても大丈夫！最初にある `{` から最後の `}` までを撃ち抜くわ💋
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
                raise ValueError("JSONブロックが見つかりませんでした。")
                
            # JSON部分だけをスナイプ！
            json_str = response[start_idx:end_idx + 1]
            
            # 整理された結果をパース
            cleaned_data = json.loads(json_str)
            log.info("✅ [Reflector] 記憶の再構築（パース）に成功しました！")
            return cleaned_data
            
        except (json.JSONDecodeError, ValueError) as e:
            log.error(f"❌ [Reflector] 司書がJSONのフォーマットを間違えました: {e}\nResponse: {response}")
            return None