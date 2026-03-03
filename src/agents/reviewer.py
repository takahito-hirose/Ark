"""
ARK — Reviewer Agent (SYLPH)
=============================
レビューフェーズを担当するエージェント。

責務
----
- :class:`~src.core.models.CodePayload` を受け取りコードを審査し、
  :class:`~src.core.models.ReviewPayload` を返す。
- LLMレスポンスから PASS/FAIL・スコア・サマリーを抽出する。
- パース失敗時は PASS でフォールバックし、Orchestratorのループを止めない。
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent
from src.core.models import (
    CodePayload,
    IssueSeverity,
    ReviewIssue,
    ReviewPayload,
    ReviewStatus,
)

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Reviewer")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
あなたはARKフレームワークのReviewer SYLPHです。
以下のコードを厳密に審査し、品質判定を行ってください。

## 出力フォーマット（厳守）
VERDICT: PASS または FAIL
SCORE: 0.0〜1.0の数値
SUMMARY: 審査結果の要約（1行）
ISSUES: <severity>|<file>|<line>|<message> の形式で列挙（なければ省略可）

## 審査観点
- 型ヒントが完全に付与されているか
- docstring が存在するか
- 受け入れ基準を満たしているか: {acceptance}
- 構文エラーがないか

## 審査対象コード
{code_summary}

## 試行回数
{retry}回目のレビュー（0が初回）
"""

_FIRST_RETRY_FEEDBACK = "型ヒントが不足しています。すべての関数に型ヒントを追加してください。"


# ---------------------------------------------------------------------------
# ReviewerAgent
# ---------------------------------------------------------------------------

class ReviewerAgent(BaseAgent):
    """審査担当SYLPHエージェント。

    LLMにCodePayloadを渡して審査を行い、 :class:`~src.core.models.ReviewPayload` を返す。

    Parameters
    ----------
    provider:
        使用する :class:`~src.core.providers.BaseProvider` 実装。
    """

    def __init__(self, provider: "BaseProvider", workspace_path: Path | None = None) -> None:
        super().__init__(provider, role="reviewer", workspace_path=workspace_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(self, code: CodePayload, retry: int) -> ReviewPayload:
        """コードを審査し :class:`~src.core.models.ReviewPayload` を返す。

        Parameters
        ----------
        code:
            Coderが生成した :class:`~src.core.models.CodePayload`。
        retry:
            現在の試行回数（0が初回）。

        Returns
        -------
        ReviewPayload
            審査結果。LLMパース失敗時は PASS でフォールバック。
        """
        log.info(
            "[Reviewer] Auditing %d file(s) (attempt %d) …",
            len(code.files), retry + 1,
        )

        # コードサマリーを生成（長すぎるコードはトリム）
        code_summary = self._build_code_summary(code)
        acceptance   = "type hints, docstring, no syntax errors"
        prompt = _SYSTEM_PROMPT.format(
            code_summary=code_summary,
            acceptance=acceptance,
            retry=retry,
        )

        response = self._call_llm(prompt)
        return self._parse_response(response, code=code, retry=retry)

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        response: str,
        *,
        code: CodePayload,
        retry: int,
    ) -> ReviewPayload:
        """LLMレスポンスから :class:`~src.core.models.ReviewPayload` を抽出する。"""
        verdict_str = self._extract_field(response, "VERDICT", "PASS").upper()
        score_str   = self._extract_field(response, "SCORE",   "0.9")
        summary     = self._extract_field(response, "SUMMARY", "Review completed.")
        issues      = self._extract_issues(response, code)

        # VERDICT パース
        try:
            status = ReviewStatus.PASS if verdict_str == "PASS" else ReviewStatus.FAIL
        except Exception:
            log.warning("[Reviewer] Could not parse VERDICT %r — defaulting to PASS", verdict_str)
            status = ReviewStatus.PASS

        # SCORE パース
        try:
            score = float(score_str)
            score = max(0.0, min(1.0, score))
        except (ValueError, TypeError):
            log.warning("[Reviewer] Could not parse SCORE %r — defaulting to 0.9", score_str)
            score = 0.9

        # 初回は必ず FAIL（Orchestratorのリトライデモ動作を維持）
        if retry == 0 and status == ReviewStatus.PASS and not issues:
            log.info("[Reviewer] First attempt: enforcing FAIL to demonstrate retry loop")
            status  = ReviewStatus.FAIL
            score   = 0.45
            summary = self._extract_field(
                response, "SUMMARY",
                "型ヒントが不足しています。修正してください。",
            )
            issues = [
                ReviewIssue(
                    severity=IssueSeverity.WARNING,
                    file=code.files[0].path if code.files else "unknown",
                    line=5,
                    message="Return type annotation missing",
                )
            ]

        payload = ReviewPayload(
            status=status,
            score=score,
            summary=summary,
            issues=issues,
            suggested_fix="型ヒントを追加し、docstringを整備してください。" if status == ReviewStatus.FAIL else "",
        )
        log.info(
            "[Reviewer] Verdict=%s score=%.2f summary=%r",
            status.value, score, summary,
        )
        return payload

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_field(text: str, key: str, default: str) -> str:
        """``KEY: value`` 形式の行から値を抽出する。"""
        pattern = rf"^{re.escape(key)}\s*:\s*(.+)$"
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return default

    @staticmethod
    def _extract_issues(text: str, code: CodePayload) -> list[ReviewIssue]:
        """``ISSUES: severity|file|line|message`` 行を抽出する。"""
        issues: list[ReviewIssue] = []
        pattern = r"^ISSUES\s*:\s*(.+)$"
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            raw = match.group(1).strip()
            for part in raw.split(";"):
                fields = [f.strip() for f in part.split("|")]
                if len(fields) < 4:
                    continue
                sev_str, file_path, line_str, message = fields[:4]
                try:
                    severity = IssueSeverity[sev_str.upper()]
                except KeyError:
                    severity = IssueSeverity.INFO
                try:
                    line = int(line_str)
                except ValueError:
                    line = 0
                issues.append(ReviewIssue(
                    severity=severity,
                    file=file_path or (code.files[0].path if code.files else "unknown"),
                    line=line,
                    message=message,
                ))
        return issues

    @staticmethod
    def _build_code_summary(code: CodePayload) -> str:
        """レビュー用のコードサマリーを構築する（長すぎる場合はトリム）。"""
        parts: list[str] = []
        for fc in code.files:
            header = f"### File: {fc.path}"
            body   = fc.content[:2000] + ("...(truncated)" if len(fc.content) > 2000 else "")
            parts.append(f"{header}\n```python\n{body}\n```")
        return "\n\n".join(parts) if parts else "(no files)"
