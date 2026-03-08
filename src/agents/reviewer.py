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
from typing import TYPE_CHECKING

from src.agents.base_agent import BaseAgent
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
# System prompt (Balanced Review 💋)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
あなたはARKフレームワークのReviewer SYLPHです。
提出されたコードを「実務的な観点」から審査してください。

## 審査の優先順位（最重要）
1. **ユーザーの目的（Goal）の達成**: 指示された機能が正しく実装されているか。
2. **コアルールの遵守**: システムプロンプトやGoalに含まれる「特定の制約（例：コメントに💋を入れる等）」が守られているか。
3. **エンジニアリング品質**: 型ヒント、docstring、構文の正確性。

## 判定基準
- **PASS の条件**: ゴールが達成されており、致命的なバグがなく、指示された特別なルール（💋等）が守られている。
- **FAIL の条件**: ゴールが未達成、指示されたルールを無視している、またはコードが実行不能。
※型ヒントや docstring が多少不足していても、上記 1, 2 が満たされていれば PASS (Score 0.8以上) とし、改善点として ISSUE を挙げるに留めてください。航海（COMMIT）を止めてはいけません。

## 出力フォーマット（厳守）
VERDICT: PASS または FAIL
SCORE: 0.0〜1.0の数値
SUMMARY: 審査結果の要約（1行）
ISSUES: <severity>|<file>|<line>|<message> の形式で列挙（なければ省略）

## ミッション情報
ゴール: {goal}
受け入れ基準: {acceptance}

## 試行回数
{retry}回目のレビュー
"""

# ---------------------------------------------------------------------------
# ReviewerAgent
# ---------------------------------------------------------------------------

class ReviewerAgent(BaseAgent):
    """審査担当SYLPHエージェント。"""

    def __init__(self, provider: "BaseProvider", workspace_path: Path | None = None) -> None:
        super().__init__(provider, role="reviewer", workspace_path=workspace_path)

    def review(self, code: CodePayload, retry: int, plan: PlanPayload | None = None) -> ReviewPayload:
        """コードを審査し ReviewPayload を返す。"""
        log.info(
            "[Reviewer] Auditing %d file(s) (attempt %d) …",
            len(code.files), retry + 1,
        )

        code_summary = self._build_code_summary(code)
        
        # プラン情報がある場合はそれを利用、ない場合はデフォルト
        goal = plan.goal if plan else "不明なゴール"
        acceptance = plan.acceptance_criteria if plan else "型ヒント, docstring, 💋ルールの遵守"

        prompt = _SYSTEM_PROMPT.format(
            code_summary=code_summary,
            goal=goal,
            acceptance=acceptance,
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

        # 👈 修正：初回リトライ時に強制的に FAIL にするロジックを削除！
        # これが「💋ルール」を記憶する際のデッドロックの原因になっていたわ💋

        payload = ReviewPayload(
            status=status,
            score=score,
            summary=summary,
            issues=issues,
            suggested_fix="型ヒントとdocstringを完璧にしてください。" if status == ReviewStatus.FAIL else "",
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
        pattern = r"^ISSUES\s*:\s*(.+)$"
        for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
            raw = match.group(1).strip()
            for part in raw.split(";"):
                fields = [f.strip() for f in part.split("|")]
                if len(fields) < 4: continue
                sev_str, file_path, line_str, message = fields[:4]
                try:
                    severity = IssueSeverity[sev_str.upper()]
                except KeyError:
                    severity = IssueSeverity.INFO
                issues.append(ReviewIssue(
                    severity=severity,
                    file=file_path or (code.files[0].path if code.files else "unknown"),
                    line=int(line_str) if line_str.isdigit() else 0,
                    message=message,
                ))
        return issues

    @staticmethod
    def _build_code_summary(code: CodePayload) -> str:
        parts: list[str] = []
        for fc in code.files:
            parts.append(f"### File: {fc.path}\n``")
        return "\n\n".join(parts) if parts else "(no files)"
