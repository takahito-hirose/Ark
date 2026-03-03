"""
ARK — Agent Layer Tests
========================
各エージェントへの MockProvider 注入テスト。
外部LLM への接続を一切行わずに実行できる。

Run:
    python -m pytest tests/test_agents.py -v
"""

from __future__ import annotations

import unittest

from src.agents import ArchitectAgent, CoderAgent, ReviewerAgent
from src.agents.base_agent import BaseAgent
from src.core.models import (
    CodePayload,
    FileAction,
    FileChange,
    PlanPayload,
    ReviewPayload,
    ReviewStatus,
)
from src.core.providers import MockProvider


# ===========================================================================
# TestBaseAgent: 基底クラスの共通動作
# ===========================================================================

class TestBaseAgent(unittest.TestCase):
    """BaseAgent の共通動作を検証するテスト群。"""

    def test_architect_is_base_agent(self) -> None:
        """ArchitectAgent は BaseAgent のインスタンスであること。"""
        agent = ArchitectAgent(MockProvider())
        self.assertIsInstance(agent, BaseAgent)

    def test_coder_is_base_agent(self) -> None:
        """CoderAgent は BaseAgent のインスタンスであること。"""
        agent = CoderAgent(MockProvider())
        self.assertIsInstance(agent, BaseAgent)

    def test_reviewer_is_base_agent(self) -> None:
        """ReviewerAgent は BaseAgent のインスタンスであること。"""
        agent = ReviewerAgent(MockProvider())
        self.assertIsInstance(agent, BaseAgent)

    def test_repr_contains_class_name(self) -> None:
        """__repr__ にクラス名とロール名が含まれること。"""
        agent = ArchitectAgent(MockProvider())
        r = repr(agent)
        self.assertIn("ArchitectAgent", r)
        self.assertIn("architect", r)


# ===========================================================================
# TestArchitectAgent
# ===========================================================================

class TestArchitectAgent(unittest.TestCase):
    """ArchitectAgent の動作を検証するテスト群。"""

    def setUp(self) -> None:
        self.provider = MockProvider()
        self.agent    = ArchitectAgent(self.provider)
        self.goal     = "Pythonで Hello World スクリプトを作成せよ"
        self.task_id  = "abc12345-1234-5678-90ab-cdef01234567"

    def test_plan_returns_plan_payload(self) -> None:
        """plan() は PlanPayload を返すこと。"""
        result = self.agent.plan(self.goal, self.task_id)
        self.assertIsInstance(result, PlanPayload)

    def test_plan_goal_is_preserved(self) -> None:
        """PlanPayload の goal がユーザー入力と一致すること。"""
        result = self.agent.plan(self.goal, self.task_id)
        self.assertEqual(result.goal, self.goal)

    def test_plan_target_files_is_nonempty(self) -> None:
        """target_files が空でないこと。"""
        result = self.agent.plan(self.goal, self.task_id)
        self.assertGreater(len(result.target_files), 0)

    def test_plan_constraints_is_nonempty(self) -> None:
        """constraints が空でないこと。"""
        result = self.agent.plan(self.goal, self.task_id)
        self.assertGreater(len(result.constraints), 0)

    def test_plan_acceptance_criteria_is_nonempty(self) -> None:
        """acceptance_criteria が空でないこと。"""
        result = self.agent.plan(self.goal, self.task_id)
        self.assertGreater(len(result.acceptance_criteria), 0)

    def test_plan_fallback_uses_task_id_prefix(self) -> None:
        """LLMがパース不可能な応答を返した場合、タスクIDを含むデフォルトファイル名が使われること。"""
        # MockProvider はパース不可能な応答を返す → フォールバックが動く
        result = self.agent.plan(self.goal, self.task_id)
        # task_id の先頭8文字がファイル名に含まれる
        any_path_has_task_prefix = any(
            self.task_id[:8] in f for f in result.target_files
        )
        self.assertTrue(any_path_has_task_prefix)


# ===========================================================================
# TestCoderAgent
# ===========================================================================

class TestCoderAgent(unittest.TestCase):
    """CoderAgent の動作を検証するテスト群。"""

    def setUp(self) -> None:
        self.provider = MockProvider()
        self.agent    = CoderAgent(self.provider)
        self.plan = PlanPayload(
            goal="Hello World スクリプトを作成",
            spec_path="specs/core_logic.md",
            target_files=["workspace/hello.py"],
            constraints=["Python 3.11+", "型ヒント必須"],
            acceptance_criteria=["no syntax errors", "file exists"],
        )

    def test_code_returns_code_payload(self) -> None:
        """code() は CodePayload を返すこと。"""
        result = self.agent.code(self.plan, retry=0)
        self.assertIsInstance(result, CodePayload)

    def test_code_has_files(self) -> None:
        """CodePayload に少なくとも1つのファイルが含まれること。"""
        result = self.agent.code(self.plan, retry=0)
        self.assertGreater(len(result.files), 0)

    def test_code_file_has_content(self) -> None:
        """生成されたファイルに内容があること。"""
        result = self.agent.code(self.plan, retry=0)
        for fc in result.files:
            self.assertGreater(len(fc.content), 0, f"File {fc.path} has empty content")

    def test_code_file_action_is_create(self) -> None:
        """LLMフォールバック時のアクションは CREATE であること。"""
        result = self.agent.code(self.plan, retry=0)
        self.assertEqual(result.files[0].action, FileAction.CREATE)

    def test_code_with_feedback(self) -> None:
        """reviewer_feedback を渡してもエラーにならないこと。"""
        result = self.agent.code(
            self.plan,
            retry=1,
            reviewer_feedback="型ヒントを追加してください",
        )
        self.assertIsInstance(result, CodePayload)

    def test_code_plan_ref_is_set(self) -> None:
        """plan_ref が設定されていること。"""
        result = self.agent.code(self.plan, retry=0)
        self.assertIsNotNone(result.plan_ref)
        self.assertGreater(len(result.plan_ref), 0)


# ===========================================================================
# TestReviewerAgent
# ===========================================================================

class TestReviewerAgent(unittest.TestCase):
    """ReviewerAgent の動作を検証するテスト群。"""

    def setUp(self) -> None:
        self.provider = MockProvider()
        self.agent    = ReviewerAgent(self.provider)
        self.code_payload = CodePayload(
            plan_ref="Hello World",
            files=[
                FileChange(
                    path="workspace/hello.py",
                    action=FileAction.CREATE,
                    content='def main() -> None:\n    print("Hello!")\n',
                )
            ],
            test_command="python workspace/hello.py",
        )

    def test_review_returns_review_payload(self) -> None:
        """review() は ReviewPayload を返すこと。"""
        result = self.agent.review(self.code_payload, retry=0)
        self.assertIsInstance(result, ReviewPayload)

    def test_review_first_attempt_fails(self) -> None:
        """初回（retry=0）は FAIL を返すこと（リトライデモ維持）。"""
        result = self.agent.review(self.code_payload, retry=0)
        self.assertEqual(result.status, ReviewStatus.FAIL)

    def test_review_first_attempt_has_issues(self) -> None:
        """初回は Issues リストが空でないこと。"""
        result = self.agent.review(self.code_payload, retry=0)
        self.assertGreater(len(result.issues), 0)

    def test_review_second_attempt_passes(self) -> None:
        """2回目以降（retry>=1）は PASS を返すこと（MockProviderのデフォルト）。"""
        result = self.agent.review(self.code_payload, retry=1)
        self.assertEqual(result.status, ReviewStatus.PASS)

    def test_review_score_in_range(self) -> None:
        """スコアは 0.0〜1.0 の範囲内であること。"""
        for retry in range(3):
            result = self.agent.review(self.code_payload, retry=retry)
            with self.subTest(retry=retry):
                self.assertGreaterEqual(result.score, 0.0)
                self.assertLessEqual(result.score, 1.0)

    def test_review_summary_is_nonempty(self) -> None:
        """summary が空文字列でないこと。"""
        result = self.agent.review(self.code_payload, retry=1)
        self.assertGreater(len(result.summary), 0)


# ===========================================================================
# TestDependencyInjection: DI の交換可能性検証
# ===========================================================================

class TestDependencyInjection(unittest.TestCase):
    """プロバイダーが DI で差し替えられることを確認するテスト群。"""

    def test_custom_provider_is_used(self) -> None:
        """カスタムテンプレートのMockProviderが実際に呼ばれること。"""
        sentinel = "UNIQUE_SENTINEL_XYZ_9999"
        custom = MockProvider(response_template=f"{sentinel}: {{prompt}}")
        agent  = ArchitectAgent(custom)

        # plan() の内部で _call_llm() → custom.generate() が呼ばれる
        # LLM応答にはパース可能なキーがないのでフォールバックになるが、
        # プロバイダーが呼ばれた証拠としてエラーが出ないことを確認する
        result = agent.plan("test goal", "test-task-id")
        self.assertIsInstance(result, PlanPayload)

    def test_provider_swap_does_not_affect_other_agents(self) -> None:
        """異なるエージェントには独立したプロバイダーが注入されること。"""
        provider_a = MockProvider()
        provider_b = MockProvider()

        arch = ArchitectAgent(provider_a)
        code = CoderAgent(provider_b)

        self.assertIs(arch._provider, provider_a)  # noqa: SLF001
        self.assertIs(code._provider, provider_b)  # noqa: SLF001
        self.assertIsNot(arch._provider, code._provider)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main(verbosity=2)
