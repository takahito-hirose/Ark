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
from typing import TYPE_CHECKING, Any

from src.agents.base_agent import BaseAgent
from src.core.agents import build_coder_prompt, build_remediation_prompt
from src.core.models import CodePayload, FileAction, FileChange, PlanPayload

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Coder")

# ---------------------------------------------------------------------------
# Engineering Quality Rules 💋
# ---------------------------------------------------------------------------

QUALITY_RULE = """
【エンジニアリング品質の義務】
1. あなたは Python シニアエンジニアとして、すべての関数・メソッドに厳密な型ヒント (typing) を付与しなければなりません。
2. モジュールおよびすべての公開関数には、詳細な docstring を付与してください。
3. リビュアーは非常に厳格であり、型ヒントの欠如を許しません。一発でパスする「完璧なコード」を出力してください。
"""

# ---------------------------------------------------------------------------
# CoderAgent
# ---------------------------------------------------------------------------

class CoderAgent(BaseAgent):
    """実装担当SYLPHエージェント。"""

    def __init__(
        self, 
        provider: "BaseProvider", 
        workspace_path: Path | None = None,
        tools: list[Any] | None = None
    ) -> None:
        super().__init__(provider, role="coder", workspace_path=workspace_path)
        # 👈 記憶ツールは Reflector が担当するため、Coder 内では保持のみ（使用はしない）にします。

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

        # 品質ルールを制約に結合
        constraints = f"{plan.constraints}\n\n{QUALITY_RULE}"
        
        prompt = build_coder_prompt(
            goal=plan.goal,
            target_files=plan.target_files,
            constraints=constraints,
            acceptance=plan.acceptance_criteria,
            retry=retry,
            workspace_path=self._workspace_path,
            reviewer_feedback=reviewer_feedback
        )
        
        # 👈 純粋な LLM 呼び出しのみ（ツール実行ループは不要）
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
        
        enhanced_reason = f"{failure_reason}\n\n※修正時も以下のルールを厳守せよ:\n{QUALITY_RULE}"

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

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

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

        # あらゆる言語タグ（python, text, txt等）を許容する正規表現 💋
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
        main_script = py_files[0] if py_files else file_changes[0].path if file_changes else "main.py"

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
                \"\"\"Entry point.\"\"\"
                print("Hello from ARK CoderAgent!")

            if __name__ == "__main__":
                main()
        """)
        return FileChange(path=path, action=FileChange.CREATE, content=content)