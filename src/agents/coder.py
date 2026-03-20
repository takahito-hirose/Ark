"""
ARK — Coder Agent (SYLPH)
==========================
実装フェーズを担当するエージェント。

責務
----
- :class:`~src.core.models.PlanPayload` を受け取りコードを生成し、
  :class:`~src.core.models.CodePayload` を返す。
- 記憶の責務は Reflector に移譲され、純粋なコーディングマシーンとして機能する。
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

# 🌟 Coder用のシステムプロンプト（SEARCH/REPLACE 形式を徹底させるわよ！💋）
_SYSTEM_PROMPT = """\
あなたはARKフレームワークの「Coder（職人）」SYLPHです。
シニアエンジニアとして、Architectのプランに基づき、最高品質のPythonコードを実装してください。

## 🛠 行動指針
1. **ピンポイント変更（SEARCH/REPLACE）の掟**:
   既存のファイルを修正する場合、ファイル全体を再出力せず、必ず以下の `SEARCH/REPLACE` 形式を使用してください。
   
   FILE: ファイルパス
   ```python
   <<<<<<< SEARCH
   （変更前の既存コードを正確に引用）
   =======
   （変更後の新しいコード）
   >>>>>>> REPLACE
   ```

2. **新規ファイル作成**:
   既存ファイルにない場合は、通常通り `FILE: パス` の後にコードブロックを出力してください。

3. **品質**:
   型ヒント (typing)、Docstring、そしてコメントの末尾には必ず「💋」を付けること。

指示を完遂し、コード以外の余計な解説は最小限にしてください。
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
        # 🌟 FIX: 親クラスが保存してくれない場合に備えて、明示的に保持するわよ！💋
        self.workspace_path = workspace_path

    def code(self, plan: PlanPayload, retry: int, reviewer_feedback: str = "") -> CodePayload:
        """プランに基づきコードを生成する。"""
        log.info("[Coder] Generating code (attempt %d) for: %s", retry + 1, plan.target_files)

        prompt = f"Goal: {plan.goal}\nTarget Files: {plan.target_files}\n"
        if reviewer_feedback:
            prompt += f"\nReviewer Feedback (Please fix this): {reviewer_feedback}\n"
        
        # 既存ファイルのコンテキストを読み取ってプロンプトに注入（外科手術の準備！）
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
実行エラーが発生しました。これを修正してください。💋

【エラー内容】
{failure_reason}
{stacktrace}

【現在のプラン】
{plan.goal}
"""
        response = self._call_llm(_SYSTEM_PROMPT + "\n\n" + remedy_prompt)
        return self._parse_response(response, plan=plan, retry=retry)

    def _parse_response(self, response: str, *, plan: PlanPayload, retry: int) -> CodePayload:
        """
        LLMレスポンスから CodePayload を抽出する。
        🌟 賢くなったパースロジックよ！
        """
        file_changes: list[FileChange] = []
        
        # 1. 正規の "FILE: path \n ``` ... ```" 形式を検索
        pattern = r"FILE:\s*([^\n]+)\n```[a-zA-Z0-9_-]*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        for raw_path, code_body in matches:
            path = raw_path.strip()
            code = code_body.rstrip()
            if path and code:
                # SEARCH/REPLACE が含まれているかチェック
                action = FileAction.UPDATE if "<<<<<<< SEARCH" in code else FileAction.CREATE
                file_changes.append(FileChange(path=path, action=action, content=code))

        # 🌟 2. レジリエンス：もし FILE: タグがないが、コードブロックだけある場合
        if not file_changes:
            # 純粋なコードブロック ``` ... ``` を探す
            code_blocks = re.findall(r"```[a-zA-Z0-9_-]*\n(.*?)```", response, re.DOTALL)
            if code_blocks and plan.target_files:
                # 最初のコードブロックを、最初のターゲットファイルのものと見なす
                path = plan.target_files[0]
                code = code_blocks[0].rstrip()
                action = FileAction.UPDATE if "<<<<<<< SEARCH" in code else FileAction.CREATE
                file_changes.append(FileChange(path=path, action=action, content=code))
                log.info("[Coder] Resilient parse: Assumed code block belongs to %s", path)

        # 3. それでもダメならフォールバック
        if not file_changes:
            log.warning("[Coder] No valid code blocks found — using fallback")
            target_path = plan.target_files[0] if plan.target_files else "workspace/output.py"
            file_changes = [self._fallback_file_change(target_path, plan.goal, retry)]

        return CodePayload(
            plan_ref=plan.goal[:40],
            files=file_changes,
            test_command=f"python {file_changes[0].path}",
            notes=f"Generated by CoderAgent (attempt {retry + 1})",
        )

    def _read_file_from_workspace(self, path: str) -> str | None:
        """ワークスペースからファイルを読み取る。"""
        if not self.workspace_path: return None
        full_path = self.workspace_path / path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def _fallback_file_change(path: str, goal: str, retry: int) -> FileChange:
        """エラー時のフォールバック。"""
        content = textwrap.dedent(f"""\
            # ARK — Auto-generated by CoderAgent (fallback)
            # Goal: {goal}
            # Attempt: {retry + 1}
            
            def greet():
                # 💋 パースに失敗しちゃったみたい！でも挨拶はするわよ
                print("Hello from ARK CoderAgent! 💋")

            if __name__ == "__main__":
                greet()
        """)
        return FileChange(path=path, action=FileAction.CREATE, content=content)