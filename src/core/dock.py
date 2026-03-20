"""
ARK — Dock (The Autonomous Shipyard)
====================================
プロジェクトの「クローン」「環境構築」「ファイル操作」を司る。
GitHub URL からの自動接岸 (Cloning) 機能を搭載！💋
"""

from __future__ import annotations

import logging
import os
import subprocess
import shutil
import re
from pathlib import Path
from src.core.models import FileChange, FileAction
from src.core.git_tools import GitTool # 🌟 修正: git_tools.py に合わせたわよ
from src.tools.terminal import TerminalOracle # 🌟 修正: src.tools.terminal に移動したわね

log = logging.getLogger("ARK.Dock")

class Dock:
    """プロジェクトの実行環境を管理するドック。"""

    def __init__(self, workspace_root: Path, project_id: str):
        self.workspace_root = workspace_root
        self.project_id = project_id
        self.path = workspace_root / project_id
        self.git = GitTool(self.path)
        self.terminal = TerminalOracle(self.path)

    def setup_from_remote(self, repo_url: str) -> bool:
        """
        GitHub等からリポジトリをクローンし、環境をセットアップするわ！💋
        """
        log.info(f"⚓️ [Dock] Attempting to dock remote ship: {repo_url}")
        
        # 1. クローン実行
        if self.path.exists():
            log.warning(f"⚠️ [Dock] Path {self.path} already exists. Skipping clone.")
        else:
            try:
                self.workspace_root.mkdir(parents=True, exist_ok=True)
                subprocess.run(["git", "clone", repo_url, str(self.path)], check=True)
                log.info(f"✅ [Dock] Cloned successfully to {self.path}")
            except Exception as e:
                log.error(f"❌ [Dock] Failed to clone: {e}")
                return False

        # 2. 仮想環境 (venv) の構築
        self._ensure_venv()

        # 3. 作業ブランチの作成 (mainを汚さないのがレディの嗜みよ💋)
        branch_name = f"ark/task-{self.project_id[:8]}"
        self.git.create_topic_branch(branch_name)
        
        return True

    def _ensure_venv(self):
        """Pythonの仮想環境を構築して依存関係をインストールするわ。"""
        # terminal.py 側で自動的に .venv を作ってくれるけど、一応ここでもチェック
        venv_path = self.path / ".venv"
        if not venv_path.exists():
            log.info("🛡️ [Dock] Requesting Terminal Oracle to build shield (venv)...")
            # TerminalOracle の初期化時または明示的なコマンドで構築
            self.terminal.execute_command("python -m venv .venv")
        
        # requirements.txt があればインストール
        if (self.path / "requirements.txt").exists():
            log.info("📦 [Dock] Installing dependencies from requirements.txt...")
            self.terminal.execute_command("pip install -r requirements.txt")

    def write_artifacts(self, changes: list[FileChange]):
        """
        生成されたコードやパッチをファイルに書き込むわ。
        SEARCH/REPLACE 形式なら、外科手術エンジンを回すわよ！💋
        """
        for change in changes:
            target_path = self.path / change.path
            target_path.parent.mkdir(parents=True, exist_ok=True)

            if change.action == FileAction.UPDATE:
                self._apply_patch(change)
            else:
                target_path.write_text(change.content, encoding="utf-8")
                log.info(f"📝 [Dock] File written: {change.path}")

    def _apply_patch(self, change: FileChange):
        """SEARCH/REPLACE 形式のパッチを適用する外科手術エンジン。"""
        target_path = self.path / change.path
        if not target_path.exists():
            log.error(f"❌ [Dock] Patch target not found: {change.path}")
            return

        source = target_path.read_text(encoding="utf-8")
        
        # 超簡易版のパッチ適用ロジック
        try:
            # 🌟 reモジュールが必要だったのでインポートに追加したわ
            search_pattern = r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE"
            matches = re.findall(search_pattern, change.content, re.DOTALL)
            
            if not matches:
                log.warning(f"⚠️ [Dock] No patches found in the content for {change.path}. Overwriting instead.")
                target_path.write_text(change.content, encoding="utf-8")
                return

            new_source = source
            for search_text, replace_text in matches:
                if search_text in new_source:
                    new_source = new_source.replace(search_text, replace_text)
                    log.info(f"✅ [Dock] Surgically modified: {change.path}")
                else:
                    log.warning(f"⚠️ [Dock] Patch mismatch in {change.path}. Search block not found.")
            
            target_path.write_text(new_source, encoding="utf-8")
        except Exception as e:
            log.error(f"❌ [Dock] Surgery failed: {e}")