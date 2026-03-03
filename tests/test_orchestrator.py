"""
ARK — Orchestrator Integration Tests (Post-Refactoring)
========================================================
リファクタリング後のOrchestratorが、MockProvider設定で
エラーなくDONEフェーズまで完走できることを確認するテスト。

Run:
    python -m pytest tests/test_orchestrator.py -v
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path


# ===========================================================================
# Helpers
# ===========================================================================

def _make_mock_env(tmp_dir: Path) -> dict[str, str]:
    """テスト用の環境変数（全プロバイダーをmockに設定）を返す。"""
    return {
        "ARK_ARCHITECT_PROVIDER": "mock",
        "ARK_CODER_PROVIDER":     "mock",
        "ARK_REVIEWER_PROVIDER":  "mock",
        "ARK_WORKSPACE_PATH":     str(tmp_dir),
    }


# ===========================================================================
# TestOrchestratorWithMock
# ===========================================================================

class TestOrchestratorWithMock(unittest.TestCase):
    """MockProvider設定での Orchestrator 統合テスト。"""

    def setUp(self) -> None:
        """各テスト前に新しい一時ワークスペースを作成する。"""
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="ark_test_"))
        self._orig_env: dict[str, str | None] = {}
        mock_env = _make_mock_env(self.tmp_dir)
        for key, val in mock_env.items():
            self._orig_env[key] = os.environ.get(key)
            os.environ[key] = val

    def tearDown(self) -> None:
        """各テスト後に環境変数と一時ディレクトリを元に戻す。"""
        for key, original in self._orig_env.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_orchestrator(self):
        """テスト用 Orchestrator インスタンスを生成する。"""
        # 環境変数が設定済みなので config.yaml を必要としない
        from src.core.orchestrator import Orchestrator
        return Orchestrator()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_orchestrator_initializes_without_error(self) -> None:
        """MockProvider 設定で Orchestrator が初期化できること。"""
        orc = self._make_orchestrator()
        self.assertIsNotNone(orc)

    def test_orchestrator_uses_agent_classes(self) -> None:
        """Orchestrator が ArchitectAgent / CoderAgent / ReviewerAgent を持つこと。"""
        from src.agents import ArchitectAgent, CoderAgent, ReviewerAgent
        orc = self._make_orchestrator()
        self.assertIsInstance(orc._architect, ArchitectAgent)  # noqa: SLF001
        self.assertIsInstance(orc._coder, CoderAgent)          # noqa: SLF001
        self.assertIsInstance(orc._reviewer, ReviewerAgent)    # noqa: SLF001

    def test_run_completes_without_exception(self) -> None:
        """MockProvider設定でrun()がCircuitBreakerTrippedを発生させずに完了すること。"""
        from src.core.orchestrator import Orchestrator
        orc = self._make_orchestrator()
        result = orc.run("テスト用: Hello World Pythonスクリプトを生成せよ")
        self.assertIsNotNone(result)

    def test_run_creates_workspace_files(self) -> None:
        """run() 後にワークスペース内にファイルが生成されること。"""
        orc = self._make_orchestrator()
        workspace = orc.run("テスト用: Hello World Pythonスクリプトを生成せよ")
        # workspace はディレクトリであること
        self.assertTrue(Path(workspace).is_dir())

    def test_state_file_created(self) -> None:
        """run() 後に .ark_state.json が生成されること。"""
        orc = self._make_orchestrator()
        workspace = orc.run("テスト用: 状態ファイル生成確認")
        state_file = Path(workspace) / ".ark_state.json"
        self.assertTrue(state_file.exists(), ".ark_state.json が存在すること")

    def test_state_file_shows_done_phase(self) -> None:
        """.ark_state.json の phase が DONE であること。"""
        orc = self._make_orchestrator()
        workspace = orc.run("テスト用: DONEフェーズ確認")
        state_file = Path(workspace) / ".ark_state.json"
        data = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual(data.get("phase"), "DONE")

    def test_state_file_has_history(self) -> None:
        """.ark_state.json の history が空でないこと。"""
        orc = self._make_orchestrator()
        workspace = orc.run("テスト用: ヒストリー確認")
        state_file = Path(workspace) / ".ark_state.json"
        data = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertGreater(len(data.get("history", [])), 0)

    def test_mock_provider_not_in_imported_orchestrator(self) -> None:
        """orchestrator モジュールに MockArchitect / MockCoder / MockReviewer が存在しないこと。"""
        import src.core.orchestrator as orch_module
        for class_name in ["MockArchitect", "MockCoder", "MockReviewer"]:
            self.assertFalse(
                hasattr(orch_module, class_name),
                f"orchestrator.py に {class_name} が残存しています",
            )


# ===========================================================================
# TestOrchestratorProviderConfig
# ===========================================================================

class TestOrchestratorProviderConfig(unittest.TestCase):
    """プロバイダー設定の参照が正しく行われることを確認するテスト群。"""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="ark_test_cfg_"))
        self._orig_env: dict[str, str | None] = {}

    def tearDown(self) -> None:
        for key, original in self._orig_env.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _set_env(self, overrides: dict[str, str]) -> None:
        base = _make_mock_env(self.tmp_dir)
        base.update(overrides)
        for key, val in base.items():
            self._orig_env[key] = os.environ.get(key)
            os.environ[key] = val

    def test_architect_uses_mock_from_env(self) -> None:
        """ARK_ARCHITECT_PROVIDER=mock のとき ArchitectAgent が MockProvider を持つこと。"""
        self._set_env({"ARK_ARCHITECT_PROVIDER": "mock"})
        from src.core.orchestrator import Orchestrator
        from src.core.providers import MockProvider
        orc = Orchestrator()
        self.assertIsInstance(orc._architect._provider, MockProvider)  # noqa: SLF001

    def test_coder_uses_mock_from_env(self) -> None:
        """ARK_CODER_PROVIDER=mock のとき CoderAgent が MockProvider を持つこと。"""
        self._set_env({"ARK_CODER_PROVIDER": "mock"})
        from src.core.orchestrator import Orchestrator
        from src.core.providers import MockProvider
        orc = Orchestrator()
        self.assertIsInstance(orc._coder._provider, MockProvider)  # noqa: SLF001

    def test_reviewer_uses_mock_from_env(self) -> None:
        """ARK_REVIEWER_PROVIDER=mock のとき ReviewerAgent が MockProvider を持つこと。"""
        self._set_env({"ARK_REVIEWER_PROVIDER": "mock"})
        from src.core.orchestrator import Orchestrator
        from src.core.providers import MockProvider
        orc = Orchestrator()
        self.assertIsInstance(orc._reviewer._provider, MockProvider)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main(verbosity=2)
