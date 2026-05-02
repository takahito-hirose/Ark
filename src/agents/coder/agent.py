"""
ARK — Coder Agent (SYLPH)
==========================
Phase 15: Domain-Driven Edition
実装フェーズを担当するエージェント。解析能力を極限まで高め、
Telescopeの検索結果（神経系）を完全に同期した強化版よ💋
※プロンプトのコアは Skills.md に移譲されました！
※Laziness（手抜き）を絶対許さないフルコード出力仕様！
"""

from __future__ import annotations

import logging
import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Callable

from src.agents.base_agent import BaseAgent
from src.core.models import CodePayload, FileAction, FileChange

if TYPE_CHECKING:
    from src.core.providers import BaseProvider
    from src.core.models import PlanPayload

log = logging.getLogger("ARK.Coder")

class CoderAgent(BaseAgent):
    """コード生成を担当するSYLPHエージェント。"""

    def __init__(
        self, 
        provider: "BaseProvider", 
        workspace_path: Path | None = None,
        on_token_usage: Optional[Callable[[int], None]] = None,
        on_thought: Optional[Callable[[str, str, str, str], None]] = None  # 🌟 NEW: 思考キャッチ用
    ) -> None:
        super().__init__(
            provider, 
            role="coder", 
            workspace_path=workspace_path, 
            on_token_usage=on_token_usage,
            on_thought=on_thought  # 🌟 BaseAgentにパススルー！
        )

    def code(self, plan: PlanPayload, retry: int, reviewer_feedback: str = "") -> CodePayload:
        """プランに基づきコードを生成する。"""
        log.info("[Coder] Generating code (attempt %d) for: %s", retry + 1, plan.target_files)

        search_results = getattr(plan, "search_results", "")
        constraints = getattr(plan, "constraints", [])
        constraints_text = "\n".join([f"- {c}" for c in constraints]) if constraints else "None"

        # 🌟 既存ファイルの現在の中身を読み込む
        context = ""
        unique_targets = list(dict.fromkeys(plan.target_files))
        for target in unique_targets:
            target_path = self._workspace_path / Path(target).name if self._workspace_path else Path(target).name
            if target_path.exists():
                try:
                    content = target_path.read_text(encoding="utf-8")
                    context += f"### File: {target_path.name} (Current Content)\n```python\n{content}\n```\n\n"
                except Exception:
                    context += f"### File: {target_path.name}\n(This is a new file to be created. It is currently EMPTY.)\n\n"
            else:
                context += f"### File: {target_path.name}\n(This is a new file to be created. It is currently EMPTY.)\n\n"

        # 🌟 動的コンテキストの構築
        dynamic_context = f"""
        ## Task Details
        GOAL: {plan.goal}
        CONSTRAINTS: {constraints_text}

        ## Latest Research Data (Priority Knowledge)
        {search_results}

        ## Target Files Content
        {context}

        Attempt: {retry + 1}
        ## Reviewer Feedback from previous failure:
        {reviewer_feedback}

        【⚠️重要・絶対遵守⚠️】
        1. 外部ライブラリを使用する場合は、必ず `FILE: requirements.txt` を出力すること。
        2. 実行時にユーザー入力を待つ `input()` は絶対に使用禁止。自動実行可能なコードにすること。
        """

        response = self._call_llm(dynamic_context)
        return self._parse_response(response, plan=plan, retry=retry)

    def remediate(self, plan: PlanPayload, retry: int, failure_reason: str, stacktrace: str, current_source: str, attempt_history: list[Any]) -> CodePayload:
        """実行エラー時の自己修復コードを生成する。"""
        log.info("[Coder] Self-healing initiated (attempt %d)...", retry + 1)
        
        unique_targets = list(dict.fromkeys(plan.target_files)) if plan.target_files else ["unknown.py"]
        targets_str = ", ".join(unique_targets)

        # 🌟 動的コンテキストの構築（自己修復用）
        dynamic_context = f"""
        ## Error Remediation Task
        The previous execution resulted in an error. Please fix the issue and output the ENTIRE corrected code.

        GOAL: {plan.goal}
        TARGET FILES: {targets_str}

        [ERROR REASON]
        {failure_reason}

        [STACKTRACE]
        {stacktrace}

        ## Current Source Code
        {current_source}
        """

        if "Timeout" in failure_reason or "Timeout" in stacktrace:
            dynamic_context += "\n\n🚨 前回の実行はタイムアウトしたわ。無限ループや外部通信のハング、または input() の待ち状態がないか徹底的にチェックして修正して！"
        
        response = self._call_llm(dynamic_context)
        return self._parse_response(response, plan=plan, retry=retry)

    def _parse_response(self, response: str, *, plan: PlanPayload, retry: int) -> CodePayload:
        """
        LLMレスポンスから執念深くコードを抽出するわよ💋
        ※Phase 15: フルコード出力に特化し、SEARCH/REPLACEのパーサーを削除しました！
        """
        file_changes: list[FileChange] = []
        updated_paths = set()
        
        # 🌟 1. FILE: path + コードブロック の抽出 (フルコード版)
        pattern = r"(?:FILE|File|file|FilePath)[*:\s]*([^\n\s]+)\s*\n+```[a-zA-Z0-9_-]*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        for raw_path, code_body in matches:
            path = raw_path.strip().strip("`").strip("*").strip(":")
            code = code_body.rstrip()
            if path and code and path not in updated_paths:
                file_changes.append(FileChange(path=path, action=FileAction.UPDATE, content=code))
                updated_paths.add(path)
                log.info("[Coder] Parsed full code for: %s", path)

        # 🌟 2. 【救済策】タグはないがコードブロックがある場合
        if not file_changes:
            code_blocks = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", response, re.DOTALL)
            for i, block in enumerate(code_blocks):
                code = block.rstrip()
                if not code: continue

                path = ""
                # コードブロックの1行目がコメントでファイル名っぽい場合
                first_line = code.split('\n')[0].strip()
                if first_line.startswith(("#", "//")) and "." in first_line:
                    path = first_line.strip("#/ ").strip()

                if not path and i < len(plan.target_files):
                    path = plan.target_files[i]

                if not path and ("==" in code or "ascii-magic" in code.lower()):
                    path = "requirements.txt"

                if path and path not in updated_paths:
                    file_changes.append(FileChange(path=path, action=FileAction.UPDATE, content=code))
                    updated_paths.add(path)
                    log.info("[Coder] Fallback parsed full code for: %s", path)

        # 🌟 3. 最終フォールバック
        if not file_changes:
            log.warning("[Coder] Parsing failed — using emergency fallback")
            target_path = plan.target_files[0] if plan.target_files else "main.py"
            file_changes = [self._fallback_file_change(target_path, plan.goal, retry)]

        return CodePayload(
            plan_ref=plan.goal[:40],
            files=file_changes,
            test_command=f"python {file_changes[0].path}",
            notes=f"Generated by CoderAgent (attempt {retry + 1})",
        )

    @staticmethod
    def _fallback_file_change(path: str, goal: str, retry: int) -> FileChange:
        content = textwrap.dedent(f"""\
            # ARK — Emergency Fallback 💋
            # {goal}
            
            if __name__ == "__main__":
                print("解析に失敗したみたい。もう一度具体的な指示をちょうだい💋")
        """)
        return FileChange(path=path, action=FileAction.UPDATE, content=content)