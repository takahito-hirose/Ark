"""
ARK — Coder Agent (SYLPH)
==========================
実装フェーズを担当するエージェント。解析能力を極限まで高め、
Telescopeの検索結果（神経系）を完全に同期した強化版よ💋
SEARCH/REPLACE パッチの検出能力を極限まで高めた外科医仕様よ！
"""

from __future__ import annotations

import logging
import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Callable

from src.agents.base_agent import BaseAgent
# 🌟 中央のプロンプト工場から、最強の指示書ビルダーをインポート！
from src.core.agents import build_coder_prompt, build_remediation_prompt
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
        on_token_usage: Optional[Callable[[int], None]] = None
    ) -> None:
        super().__init__(provider, role="coder", workspace_path=workspace_path, on_token_usage=on_token_usage)
        self.workspace_path = workspace_path

    def code(self, plan: PlanPayload, retry: int, reviewer_feedback: str = "") -> CodePayload:
        """プランに基づきコードを生成する。"""
        log.info("[Coder] Generating code (attempt %d) for: %s", retry + 1, plan.target_files)

        # 🌟 PlanPayload に格納されている検索結果を安全に取り出す
        search_results = getattr(plan, "search_results", "")

        # 🌟 直書きプロンプトを廃止し、中央工場から生成！
        prompt = build_coder_prompt(
            goal=plan.goal,
            target_files=plan.target_files,
            constraints=plan.constraints if hasattr(plan, "constraints") else [],
            acceptance=plan.acceptance_criteria if hasattr(plan, "acceptance_criteria") else [],
            retry=retry,
            workspace_path=self.workspace_path,
            reviewer_feedback=reviewer_feedback,
            search_results=search_results  # 🔭 ここで最新の検索知識を注入！
        )

        # 🌟 [CRITICAL FIX] Coderくんに「道具の調達」と「パッチ形式」を徹底させる！💋
        prompt += (
            "\n\n【⚠️重要・絶対遵守⚠️】\n"
            "1. 外部ライブラリを使用する場合は、必ず `FILE: requirements.txt` を出力すること。\n"
            "2. 既存ファイルの修正は、必ず `<<<< SEARCH`, `====`, `>>>> REPLACE` の形式で出力すること。\n"
            "3. 実行時にユーザー入力を待つ `input()` は絶対に使用禁止。自動実行可能なコードにすること。"
        )

        response = self._call_llm(prompt)
        return self._parse_response(response, plan=plan, retry=retry)

    def remediate(self, plan: PlanPayload, retry: int, failure_reason: str, stacktrace: str, current_source: str, attempt_history: list[Any]) -> CodePayload:
        """実行エラー時の自己修復コードを生成する。"""
        log.info("[Coder] Self-healing initiated (attempt %d)...", retry + 1)
        
        prompt = build_remediation_prompt(
            goal=plan.goal,
            target_files=plan.target_files,
            retry=retry,
            workspace_path=self.workspace_path,
            failure_reason=failure_reason,
            stacktrace=stacktrace,
            current_source=current_source,
            attempt_history=attempt_history
        )

        # タイムアウト対策の念押し💋
        if "Timeout" in failure_reason or "Timeout" in stacktrace:
            prompt += "\n\n🚨 前回の実行はタイムアウトしたわ。無限ループや外部通信のハング、または input() の待ち状態がないか徹底的にチェックして修正して！"
        
        response = self._call_llm(prompt)
        return self._parse_response(response, plan=plan, retry=retry)

    def _parse_response(self, response: str, *, plan: PlanPayload, retry: int) -> CodePayload:
        """
        LLMレスポンスから執念深くコードとパッチを抽出するわよ💋
        """
        file_changes: list[FileChange] = []
        
        # 🌟 1. SEARCH/REPLACE パッチブロックの抽出を優先！
        # ファイル名がブロックの外にある場合と、中にある場合両方に対応するわ💋
        patch_pattern = r"(?:FILE|File|file|FilePath)[*:\s]*([^\n\s]+)\s*\n+.*?(<{3,}\s*SEARCH.*?>{3,}\s*REPLACE)"
        patch_matches = re.findall(patch_pattern, response, re.DOTALL | re.IGNORECASE)

        for raw_path, patch_body in patch_matches:
            path = raw_path.strip().strip("`").strip("*").strip(":")
            if path and patch_body:
                file_changes.append(FileChange(path=path, action=FileAction.UPDATE, content=patch_body.strip()))
                log.info("[Coder] Parsed patch (UPDATE): %s", path)

        # 🌟 2. 通常の生成形式（FILE: path + コードブロック）
        updated_paths = {fc.path for fc in file_changes}
        pattern = r"(?:FILE|File|file|FilePath)[*:\s]*([^\n\s]+)\s*\n+```[a-zA-Z0-9_-]*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        for raw_path, code_body in matches:
            path = raw_path.strip().strip("`").strip("*").strip(":")
            code = code_body.rstrip()
            if path and code and path not in updated_paths:
                # ブロックの中に SEARCH が入っている場合も UPDATE として扱う
                action = FileAction.UPDATE if "<<<<<<< SEARCH" in code else FileAction.CREATE
                file_changes.append(FileChange(path=path, action=action, content=code))

        # 🌟 3. 【救済策・統合版】タグはないがコードブロックがある場合
        if not file_changes:
            code_blocks = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", response, re.DOTALL)
            for i, block in enumerate(code_blocks):
                code = block.rstrip()
                if not code: continue

                path = ""
                first_line = code.split('\n')[0].strip()
                if first_line.startswith(("#", "//")) and "." in first_line:
                    path = first_line.strip("#/ ").strip()

                if not path and i < len(plan.target_files):
                    path = plan.target_files[i]

                if not path and ("==" in code or "ascii-magic" in code.lower()):
                    path = "requirements.txt"

                if path:
                    action = FileAction.UPDATE if "<<<<<<< SEARCH" in code else FileAction.CREATE
                    file_changes.append(FileChange(path=path, action=action, content=code))

        # 4. 最終フォールバック
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
        return FileChange(path=path, action=FileAction.CREATE, content=content)