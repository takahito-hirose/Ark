"""
ARK — Orchestrator Integration Tests (Post-Refactoring)
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, PropertyMock
import importlib
from src.core import config

# ===========================================================================
# Helpers
# ===========================================================================

def _make_mock_env(tmp_dir: Path) -> dict[str, str]:
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
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="ark_test_"))
        self._orig_env: dict[str, str | None] = {}
        mock_env = _make_mock_env(self.tmp_dir)
        for key, val in mock_env.items():
            self._orig_env[key] = os.environ.get(key)
            os.environ[key] = val

    def tearDown(self) -> None:
        for key, original in self._orig_env.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_orchestrator(self):
        from src.core.orchestrator import Orchestrator
        return Orchestrator(workspace_path=str(self.tmp_dir))

    def test_orchestrator_initializes_without_error(self) -> None:
        orc = self._make_orchestrator()
        self.assertIsNotNone(orc)

    def test_orchestrator_uses_agent_classes(self) -> None:
        from src.agents import ArchitectAgent, CoderAgent, ReviewerAgent
        orc = self._make_orchestrator()
        self.assertIsInstance(orc._architect, ArchitectAgent)
        self.assertIsInstance(orc._coder, CoderAgent)
        self.assertIsInstance(orc._reviewer, ReviewerAgent)

    def test_run_completes_without_exception(self) -> None:
        orc = self._make_orchestrator()
        result = orc.run("テスト用: Hello World")
        self.assertIsNotNone(result)

    def test_state_file_created(self) -> None:
        orc = self._make_orchestrator()
        workspace = orc.run("テスト用: 状態ファイル確認")
        state_file = Path(workspace) / ".ark_state.json"
        self.assertTrue(state_file.exists())

# ===========================================================================
# TestOrchestratorProviderConfig
# ===========================================================================

class TestOrchestratorProviderConfig(unittest.TestCase):
    """プロバイダー設定の参照が正しく行われることを確認するテスト群。"""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="ark_test_cfg_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # 👇 ポイント：ConfigLoader.load をパッチして、モック済みの ARKConfig を返すようにするわ！
    @patch("src.core.config.ConfigLoader.load")
    def test_architect_uses_mock_from_env(self, mock_load):
        from src.core.orchestrator import Orchestrator
        from src.core.providers import MockProvider
        from src.core.config import ARKConfig
        
        # モックが返す設定を作成
        mock_load.return_value = ARKConfig(
            architect_provider="mock",
            workspace_path=self.tmp_dir
        )
        
        orc = Orchestrator(workspace_path=str(self.tmp_dir))
        self.assertIsInstance(orc._architect._provider, MockProvider)

    @patch("src.core.config.ConfigLoader.load")
    def test_coder_uses_mock_from_env(self, mock_load):
        from src.core.orchestrator import Orchestrator
        from src.core.providers import MockProvider
        from src.core.config import ARKConfig
        
        mock_load.return_value = ARKConfig(
            coder_provider="mock",
            workspace_path=self.tmp_dir
        )
        
        orc = Orchestrator(workspace_path=str(self.tmp_dir))
        self.assertIsInstance(orc._coder._provider, MockProvider)

    @patch("src.core.config.ConfigLoader.load")
    def test_reviewer_uses_mock_from_env(self, mock_load):
        from src.core.orchestrator import Orchestrator
        from src.core.providers import MockProvider
        from src.core.config import ARKConfig
        
        mock_load.return_value = ARKConfig(
            reviewer_provider="mock",
            workspace_path=self.tmp_dir
        )
        
        orc = Orchestrator(workspace_path=str(self.tmp_dir))
        self.assertIsInstance(orc._reviewer._provider, MockProvider)