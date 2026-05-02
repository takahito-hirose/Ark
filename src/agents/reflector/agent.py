"""
ARK — Reflector Agent (SYLPH)
=============================
Phase 15: Domain-Driven Edition
振り返りフェーズと、記憶のガベージコレクション（大掃除）を担当するエージェント。
※プロンプトのコア（分析手法とTOOL_CALL形式）は Skills.md に移譲されました！

責務
----
- 完了したミッションとコードを分析し、TOOL_CALLを発行して記憶を永続化する。
- 🧹 乱雑になった記憶を読み込み、自律的に整理整頓（GC）を行う司書モード💋
- 🧠 苦労の履歴と失敗フラグから、アンチパターン（地雷マップ）を学習する！
"""

from __future__ import annotations

import logging
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, Dict

from src.agents.base_agent import BaseAgent
# 🌟 旧: from src.core.agents import build_reflector_prompt, build_gc_prompt (完全パージ！)
from src.core.models import CodePayload, PlanPayload, ExecutionAttempt

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
        on_token_usage: Optional[Callable[[int], None]] = None,
        on_thought: Optional[Callable[[str, str, str, str], None]] = None  # 🌟 NEW: 思考キャッチ用
    ) -> None:
        super().__init__(
            provider, 
            role="reflector", 
            workspace_path=workspace_path,
            on_token_usage=on_token_usage,
            on_thought=on_thought  # 🌟 BaseAgentにそのままパス！
        )
        self.workspace_path = workspace_path
        self.tools = tools or []

    def reflect(
        self, 
        plan: PlanPayload, 
        code: CodePayload, 
        attempt_history: list[ExecutionAttempt] | None = None,
        is_failure: bool = False
    ) -> None:
        """ゴールとコード、そして苦労の軌跡を分析し、記憶ツールを実行する。"""
        
        if is_failure:
            log.warning("⚠️ [Reflector] 致命的な敗北を検知！アンチパターンの抽出と地雷マップの作成に移行します💋")
        else:
            log.info("✨ [Reflector] ミッション完了！成功の軌跡から知見を抽出します...")

        search_results = getattr(plan, "search_results", "")
        files = [fc.path for fc in code.files]

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

        # 🌟 Phase 15: 動的コンテキストの構築 (Skills.mdと合体して最強の分析を行うよ！)
        search_hint = f"\n## New Insights (Research Data)\n{search_results}\nArchive any new specifications or differences found." if search_results else ""
        history_hint = f"\n## Trial & Error History\n{history_str}\nAnalyze this history to extract 'Failure Patterns' and their 'Success Snippets'." if history_str else ""
        
        failure_directive = ""
        if is_failure:
            failure_directive = """
            ## 🚨 CRITICAL FAILURE ANALYSIS MODE 🚨
            The mission ultimately FAILED after maximum retries. 
            Your primary objective is NO LONGER to extract success stories, but to deeply analyze WHY the process failed and to map out the "Anti-Patterns" (Landmines).
            - What logic was fundamentally flawed?
            - What repeating errors occurred during the attempt history?
            - Extract these fatal mistakes and formulate clear "Avoidance Rules" (Negative Knowledge) to prevent future agents from making the same errors.
            """

        dynamic_context = f"""
        {failure_directive}

        ## Extraction Targets
        {search_hint}
        {history_hint}

        ## Mission Data
        Goal: {plan.goal}
        Modified Files: {", ".join(files)}
        """
        
        response = self._call_llm(dynamic_context)
        self._handle_tool_calls(response)

    def _handle_tool_calls(self, response: str) -> None:
        """LLMのレスポンスから TOOL_CALL コマンドを検知して直接実行する💋"""
        tool_executed = False
        for line in response.split("\n"):
            line = line.strip()
            
            # Skills.mdで <analysis> タグを使わせているけど、
            # 行単位の prefix チェックだから全く壊れず安全に抽出できるわ！
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

        # 🌟 Phase 15: Skills.md の出力を上書き（Override）する司書用プロンプト！
        gc_prompt = f"""
        【⚠️ IMPORTANT OVERRIDE】
        This is a special sub-task (Garbage Collection). IGNORE your standard output format (TOOL_CALLs, etc.).
        Analyze the provided "Current Memory Dump" and reconstruct it following these rules:

        ## Reorganization Rules
        1. Deduplication: Merge similar rules or experiences.
        2. Conflict Resolution: If old and new information conflict, keep the most recent or generic one.
        3. Clean Up: Remove meaningless placeholder data (e.g., "rule_name", "experience_summary").
        4. Output Format: Output ONLY a valid JSON string. Do not include markdown code blocks like ```json.

        ## Current Memory Dump
        {current_memory_dump}
        """

        response = self._call_llm(gc_prompt)
        
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            
            if start_idx == -1 or end_idx == -1 or start_idx > end_idx:
                raise ValueError("JSONブロックが見つかりませんでした。")
                
            json_str = response[start_idx:end_idx + 1]
            cleaned_data = json.loads(json_str)
            log.info("✅ [Reflector] 記憶の再構築（パース）に成功しました！")
            return cleaned_data
            
        except (json.JSONDecodeError, ValueError) as e:
            log.error(f"❌ [Reflector] 司書がJSONのフォーマットを間違えました: {e}\nResponse: {response}")
            return None