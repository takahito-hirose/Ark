"""
ARK — Coder Agent (SYLPH)
==========================
実装フェーズを担当するエージェント。

責務
----
- :class:`~src.core.models.PlanPayload` を受け取りコードを生成し、
  :class:`~src.core.models.CodePayload` を返す。
- LLMレスポンスからファイルパスとコード本体を抽出する。
- パース失敗時はセーフなフォールバックコードを使用してループを継続する。
"""

from __future__ import annotations

import logging
import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent
from src.core.agents import build_coder_prompt, build_remediation_prompt
from src.core.models import CodePayload, FileAction, FileChange, PlanPayload

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Coder")

# ---------------------------------------------------------------------------
# System prompt & Rules
# ---------------------------------------------------------------------------

DEPENDENCY_RULE = """
【依存関係の鉄則】
1. 新しい外部ライブラリを `import` した場合は、必ず `requirements.txt` も出力し、そのパッケージ名を追加すること。
2. `requirements.txt` は常に最新の `import` 状況と同期していること。
3. 標準ライブラリ（os, sys, json, pathlib 等）は `requirements.txt` に含めないこと。
"""

_SYSTEM_PROMPT = f"""\
あなたはARKフレームワークのCoder SYLPHです。
以下の実装計画に基づいてPythonコードを生成してください。

## 出力フォーマット（厳守）
FILE: <ファイルパス>
```python
<生成するコード全体>
```

## 制約
- Python 3.11+ に準拠すること
- すべての関数・メソッドに型ヒントを付けること
- モジュールに docstring を付けること
{DEPENDENCY_RULE}

## 実装計画
ゴール: {{goal}}
対象ファイル: {{target_files}}
制約: {{constraints}}
受け入れ基準: {{acceptance}}

## 試行回数
{{retry}}回目の実装（0が初回）

{{reviewer_feedback}}
"""


# ---------------------------------------------------------------------------
# CoderAgent
# ---------------------------------------------------------------------------

class CoderAgent(BaseAgent):
    """実装担当SYLPHエージェント。"""

    def __init__(self, provider: "BaseProvider", workspace_path: Path | None = None) -> None:
        super().__init__(provider, role="coder", workspace_path=workspace_path)

    def code(
        self,
        plan: PlanPayload,
        retry: int,
        reviewer_feedback: str = "",
    ) -> CodePayload:
        """実装計画からコードを生成する。"""
        log.info(
            "[Coder] Generating code (attempt %d) for: %s",
            retry + 1, plan.target_files,
        )

        enhanced_constraints = f"{plan.constraints}\n\n{DEPENDENCY_RULE}" if isinstance(plan.constraints, str) else plan.constraints

        prompt = build_coder_prompt(
            goal=plan.goal,
            target_files=plan.target_files,
            constraints=enhanced_constraints,
            acceptance=plan.acceptance_criteria,
            retry=retry,
            workspace_path=self._workspace_path,
            reviewer_feedback=reviewer_feedback
        )
        
        response = self._call_llm(prompt)
        return self._parse_response(response, plan=plan, retry=retry)

    def remediate(
        self,
        plan: PlanPayload,
        retry: int,
        failure_reason: str,
        stacktrace: str,
        current_source: str,
        attempt_history: list = None
    ) -> CodePayload:
        """実行エラーを分析し、修正コードを生成する。"""
        log.info("[Coder] Remediating code (attempt %d) due to: %s", retry, failure_reason)
        
        enhanced_reason = f"{failure_reason}\n\n※修正時も以下のルールを守ること:\n{DEPENDENCY_RULE}"

        prompt = build_remediation_prompt(
            goal=plan.goal,
            target_files=plan.target_files,
            retry=retry,
            workspace_path=self._workspace_path,
            failure_reason=enhanced_reason,
            stacktrace=stacktrace,
            current_source=current_source,
            attempt_history=attempt_history
        )
        
        response = self._call_llm(prompt)
        return self._parse_response(response, plan=plan, retry=retry)

    def _parse_response(
        self,
        response: str,
        *,
        plan: PlanPayload,
        retry: int,
    ) -> CodePayload:
        """LLMレスポンスから CodePayload を抽出する。"""
        target_path = plan.target_files[0] if plan.target_files else "workspace/output.py"
        file_changes: list[FileChange] = []

        # あらゆる言語タグに対応する正規表現
        pattern = r"FILE:\s*([^\n]+)\n```[a-zA-Z0-9_-]*\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)

        for raw_path, code_body in matches:
            path = raw_path.strip()
            code = code_body.rstrip()
            if path and code:
                file_changes.append(
                    FileChange(path=path, action=FileAction.CREATE, content=code)
                )
                log.debug("[Coder] Parsed file: %s (%d bytes)", path, len(code))

        if not file_changes:
            log.warning("[Coder] No valid code blocks found in LLM response — using fallback")
            file_changes = [self._fallback_file_change(target_path, plan.goal, retry)]

        # 実行対象は .py ファイルを優先
        py_files = [f.path for f in file_changes if f.path.endswith(".py")]
        main_script = py_files[0] if py_files else file_changes[0].path

        return CodePayload(
            plan_ref=plan.goal[:40],
            files=file_changes,
            test_command=f"python {main_script}",
            notes=f"Generated by CoderAgent (attempt {retry + 1})",
        )

    @staticmethod
    def _fallback_file_change(path: str, goal: str, retry: int) -> FileChange:
        """パース失敗時のフォールバック。"""
        content = textwrap.dedent(f"""\
            # ARK — Auto-generated by CoderAgent (fallback)
            # Goal: {goal}
            # Attempt: {retry + 1}
            \"\"\"ARK generated module.\"\"\"

            def main() -> None:
                print("Hello from ARK CoderAgent!")

            if __name__ == "__main__":
                main()
        """)
        return FileChange(path=path, action=FileAction.CREATE, content=content)