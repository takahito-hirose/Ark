"""
ARK — Reviewer Agent (SYLPH)
=============================
Phase 15: Domain-Driven Edition
レビューフェーズを担当するエージェント。
※プロンプトのコア（人格と出力形式）は Skills.md に移譲されました！

責務
----
- CodePayload と RunResult を受け取る。
- 実行テスト(pytest)がPASSしている場合は、「テストの改ざんがないか」「コード品質は担保されているか」に特化した審査を行う。
- テストがない場合、またはFAILの場合は、従来通りの厳格な全方位審査を行う。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from src.agents.base_agent import BaseAgent
# 🌟 旧: from src.core.agents import build_reviewer_prompt (削除！)
from src.core.models import (
    CodePayload,
    IssueSeverity,
    ReviewIssue,
    ReviewPayload,
    ReviewStatus,
    PlanPayload,
    RunResult
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

    def review(self, code: CodePayload, retry: int, plan: PlanPayload | None = None, run_result: RunResult | None = None) -> ReviewPayload:
        """コードを審査し ReviewPayload を返す。"""
        log.info(
            "[Reviewer] Auditing %d file(s) (attempt %d) …",
            len(code.files), retry + 1,
        )

        code_summary = self._build_code_summary(code)
        search_results = getattr(plan, "search_results", "") if plan else ""

        # 🌟 STEP 2: Hybrid Final Review の判定
        is_test_passed = False
        if run_result and run_result.success:
            # 構文チェックのみではない（実際にテストが実行された）か確認
            if "Syntax check passed" not in run_result.stdout:
                is_test_passed = True

        if is_test_passed:
            log.info("🤖 [Reviewer] 実行テスト(pytest)のPASSを確認。コード品質とテスト改ざんの監視モードへ移行します。")
            review_criteria = (
                "【特別審査モード】提出されたコードは既に単体テストをPASSしています。\n"
                "機能要件の不足を理由にFAILにしないでください。\n"
                "あなたの役割は以下の2点のみです。問題がなければ必ずPASSとしてください：\n"
                "1. テストの整合性: Coderがテストを無理やり通すために、テストコード自体を不適切に改ざん・削除していないか。\n"
                "2. コード品質: 可読性、保守性、命名規則、セキュリティにおいて重大な懸念やスパゲッティコード化がないか。"
            )
        else:
            log.warning("⚠️ [Reviewer] テスト未実施、またはFAILです。全方位の厳格な審査を実施します。")
            # planがなければデフォルトの厳しい基準を設定
            base_acceptance = "\n".join([f"- {c}" for c in plan.acceptance_criteria]) if plan and hasattr(plan, "acceptance_criteria") else "型ヒント, docstring, ルールの遵守"
            review_criteria = f"【厳格審査モード】\n{base_acceptance}"

        # 🌟 Phase 15: 動的コンテキストの構築 (Skills.mdのルールと合体するよ！)
        search_hint = f"\n## Research Criteria\nEnsure the following information is reflected correctly:\n{search_results}" if search_results else ""

        dynamic_context = f"""
        ## Mission Goal
        {plan.goal if plan else "不明なゴール"}

        {search_hint}

        ## Evaluation Criteria
        {review_criteria}

        ## Submitted Code
        {code_summary}
        """

        # ベースエージェントが Skills.md + dynamic_context を合体させてLLMに投げる！
        response = self._call_llm(dynamic_context)
        return self._parse_response(response, code=code, retry=retry)

    def _parse_response(
        self,
        response: str,
        *,
        code: CodePayload,
        retry: int,
    ) -> ReviewPayload:
        """LLMレスポンスから ReviewPayload を抽出する。"""
        # Skills.mdで <code_review> タグを使わせるようにしたけど、
        # この正規表現たちは文頭の `VERDICT:` などを探すから全く壊れないよ！💋
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
            suggested_fix="指摘されたコード品質の問題、またはテストの改ざんを修正してください。" if status == ReviewStatus.FAIL else "",
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
        parts: list[str] = []
        for fc in code.files:
            parts.append(f"### File: {fc.path}\n```python\n{fc.content}\n```")
        
        summary = "\n\n".join(parts)
        log.debug("[Reviewer] Built code summary (length: %d)", len(summary))
        return summary if parts else "(no files submitted)"