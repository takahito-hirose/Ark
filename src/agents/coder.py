"""
ARK — Coder Agent (SYLPH)
==========================
実装フェーズを担当するエージェント。解析能力を極限まで高めた強化版よ💋
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

# 🌟 システムプロンプトを少し優しく、かつ明確にするわよ
_SYSTEM_PROMPT = """\
あなたはARKフレームワークのエンジニア「SYLPH」です。
Architectのプランに基づき、最高品質のPythonコードを実装してください。

## 🛠 出力ルール
1. **ファイル指定の徹底**:
   各コードブロックの直前に必ず `FILE: パス` と記述してください。
   例:
   FILE: main.py
   ```python
   print("hello")
   ```

2. **既存ファイルの修正 (SEARCH/REPLACE)**:
   既存ファイルをピンポイントで直す場合は、以下の形式を守ってください。
   FILE: パス
   ```python
   <<<<<<< SEARCH
   （既存のコード）
   =======
   （新しいコード）
   >>>>>>> REPLACE
   ```
   ※ 面倒ならファイル全体を `FILE: パス` + ```python ... ``` で再出力しても構いません。

3. **品質と愛**:
   型ヒント、Docstring、コメントの末尾には必ず「💋」を付けること。

余計な解説は不要。コードこそがあなたの言葉よ。
"""

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

        prompt = f"Goal: {plan.goal}\nTarget Files: {plan.target_files}\n"
        if reviewer_feedback:
            prompt += f"\nReviewer Feedback (Please fix this): {reviewer_feedback}\n"
        
        for file_path in plan.target_files:
            content = self._read_file_from_workspace(file_path)
            if content:
                prompt += f"\n--- Current content of {file_path} ---\n{content}\n"

        response = self._call_llm(_SYSTEM_PROMPT + "\n\n" + prompt)
        return self._parse_response(response, plan=plan, retry=retry)

    def remediate(self, plan: PlanPayload, retry: int, failure_reason: str, stacktrace: str, current_source: str, attempt_history: list[Any]) -> CodePayload:
        """実行エラー時の自己修復コードを生成する。"""
        log.info("[Coder] Self-healing initiated (attempt %d)...", retry + 1)
        
        remedy_prompt = f"""
【緊急事態】実行エラーが発生しました。修正してください。💋

エラー内容:
{failure_reason}
{stacktrace}

対象ファイル: {plan.target_files}
"""
        response = self._call_llm(_SYSTEM_PROMPT + "\n\n" + remedy_prompt)
        return self._parse_response(response, plan=plan, retry=retry)

    def _parse_response(self, response: str, *, plan: PlanPayload, retry: int) -> CodePayload:
        """
        LLMレスポンスから執念深くコードを抽出するわよ💋
        """
        file_changes: list[FileChange] = []
        
        # 1. まずは「FILE: path」とコードブロックのセットを探す
        # 正規表現をさらにルーズにして、前後の空白や改行を許容するわ
        pattern = r"(?:FILE|File|file|FilePath):\s*([^\n\s]+)\s*\n+```[a-zA-Z0-9_-]*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        for raw_path, code_body in matches:
            path = raw_path.strip().strip("`").strip("*") # 装飾を取り除く
            code = code_body.rstrip()
            if path and code:
                action = FileAction.UPDATE if "<<<<<<< SEARCH" in code else FileAction.CREATE
                file_changes.append(FileChange(path=path, action=action, content=code))

        # 2. 【救済策1】タグはないがコードブロックがある場合
        if not file_changes:
            code_blocks = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", response, re.DOTALL)
            if code_blocks:
                # ターゲットファイルリストとコードブロックを順番に紐付けるわ
                for i, block in enumerate(code_blocks):
                    if i < len(plan.target_files):
                        path = plan.target_files[i]
                        code = block.rstrip()
                        action = FileAction.UPDATE if "<<<<<<< SEARCH" in code else FileAction.CREATE
                        file_changes.append(FileChange(path=path, action=action, content=code))
                        log.info("[Coder] Resilient map: Block %d -> %s", i, path)

        # 3. 【救済策2】コードの1行目にファイル名がコメントで入っている場合
        # Qwenがよくやる "# main.py" みたいなやつを拾うわよ
        if not file_changes:
             code_blocks = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", response, re.DOTALL)
             for block in code_blocks:
                 first_line = block.split('\n')[0].strip()
                 if first_line.startswith("#") and any(f in first_line for f in plan.target_files):
                     path = first_line.replace("#", "").strip()
                     file_changes.append(FileChange(path=path, action=FileAction.CREATE, content=block))

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

    def _read_file_from_workspace(self, path: str) -> str | None:
        if not self.workspace_path: return None
        full_path = self.workspace_path / path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def _fallback_file_change(path: str, goal: str, retry: int) -> FileChange:
        content = textwrap.dedent(f"""\
            # ARK — Emergency Fallback 💋
            # {goal}
            
            if __name__ == "__main__":
                print("解析に失敗したみたい。もう一度具体的な指示をちょうだい💋")
        """)
        return FileChange(path=path, action=FileAction.CREATE, content=content)