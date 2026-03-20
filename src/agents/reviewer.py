"""
ARK — Reviewer Agent (SYLPH)
=============================
レビューフェーズを担当するエージェント。

責務
----
- :class:`~src.core.models.CodePayload` を受け取りコードを審査し、
  :class:`~src.core.models.ReviewPayload` を返す。
- ユーザーの目的（Goal）とコアルールの遵守を最優先に評価する。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from src.agents.base_agent import BaseAgent
from src.core.agents import build_reviewer_prompt # 🌟 Canvasで定義した最新のプロンプトを使用！
from src.core.models import (
    CodePayload,
    IssueSeverity,
    ReviewIssue,
    ReviewPayload,
    ReviewStatus,
    PlanPayload
)

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Reviewer")

# ---------------------------------------------------------------------------
# ReviewerAgent
# ---------------------------------------------------------------------------

class ReviewerAgent(BaseAgent):
    """審査担当SYLPHエージェント。"""

    def __init__(
        self, 
        provider: "BaseProvider", 
        workspace_path: Path | None = None,
        on_token_usage: Optional[Callable[[int], None]] = None
    ) -> None:
        super().__init__(
            provider, 
            role="reviewer", 
            workspace_path=workspace_path,
            on_token_usage=on_token_usage
        )

    def review(self, code: CodePayload, retry: int, plan: PlanPayload | None = None) -> ReviewPayload:
        """コードを審査し ReviewPayload を返す。"""
        log.info(
            "[Reviewer] Auditing %d file(s) (attempt %d) …",
            len(code.files), retry + 1,
        )

        # 🌟 ここが重要！提出されたコードの中身をちゃんと文字列化するのよ💋
        code_summary = self._build_code_summary(code)
        
        # 🌟 Canvas (src/core/agents.py) で定義した中央集権的なプロンプトを呼び出すわ！
        prompt = build_reviewer_prompt(
            goal=plan.goal if plan else "不明なゴール",
            code_summary=code_summary,
            acceptance=plan.acceptance_criteria if plan else "型ヒント, docstring, 💋ルールの遵守",
            retry=retry,
        )

        response = self._call_llm(prompt)
        return self._parse_response(response, code=code, retry=retry)

    def _parse_response(
        self,
        response: str,
        *,
        code: CodePayload,
        retry: int,
    ) -> ReviewPayload:
        """LLMレスポンスから ReviewPayload を抽出する。"""
        verdict_str = self._extract_field(response, "VERDICT", "PASS").upper()
        score_str   = self._extract_field(response, "SCORE",   "0.9")
        summary     = self._extract_field(response, "SUMMARY", "Review completed.")
        issues      = self._extract_issues(response, code)

        try:
            status = ReviewStatus.PASS if "PASS" in verdict_str else ReviewStatus.FAIL
        except Exception:
            status = ReviewStatus.PASS

        try:
            score = float(score_str)
            score = max(0.0, min(1.0, score))
        except (ValueError, TypeError):
            score = 0.9

        payload = ReviewPayload(
            status=status,
            score=score,
            summary=summary,
            issues=issues,
            suggested_fix="指示された機能が不足しているか、ルールが守られていません。修正してください。" if status == ReviewStatus.FAIL else "",
        )
        log.info(
            "[Reviewer] Verdict=%s score=%.2f summary=%r",
            status.value, score, summary,
        )
        return payload

    @staticmethod
    def _extract_field(text: str, key: str, default: str) -> str:
        pattern = rf"^{re.escape(key)}\s*:\s*(.+)$"
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        return match.group(1).strip() if match else default

    @staticmethod
    def _extract_issues(text: str, code: CodePayload) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        pattern = r"([A-Z]+)\s*\|\s*([^|]+)\s*\|\s*(\d+)\s*\|\s*([^;\n]+)"
        
        # ISSUESセクションを特定して解析
        issues_match = re.search(r"ISSUES\s*:\s*(.*)", text, re.DOTALL | re.IGNORECASE)
        if issues_match:
            raw_issues = issues_match.group(1).split("\n")
            for line in raw_issues:
                match = re.search(pattern, line)
                if match:
                    sev_str, file_path, line_str, message = match.groups()
                    try:
                        severity = IssueSeverity[sev_str.upper()]
                    except KeyError:
                        severity = IssueSeverity.INFO
                    issues.append(ReviewIssue(
                        severity=severity,
                        file=file_path.strip(),
                        line=int(line_str),
                        message=message.strip(),
                    ))
        return issues

    @staticmethod
    def _build_code_summary(code: CodePayload) -> str:
        """
        提出されたすべてのファイルの中身（パッチを含む）を連結してサマリーを作るわよ。💋
        """
        parts: list[str] = []
        for fc in code.files:
            # 🌟 fc.content (パッチの中身) をちゃんと含めるのが「開眼」のポイント！
            parts.append(f"### File: {fc.path}\n```python\n{fc.content}\n```")
        
        summary = "\n\n".join(parts)
        log.debug("[Reviewer] Built code summary (length: %d)", len(summary))
        return summary if parts else "(no files submitted)"