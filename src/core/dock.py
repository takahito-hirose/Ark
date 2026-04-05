"""
ARK — Dock (The Autonomous Shipyard)
====================================
Phase 14: The Merge Protocol (File Lock & Queue)
プロジェクトの「クローン」「環境構築」「ファイル操作」を司る。
複数のワーカーが同時に書き込んでも競合しないよう、ファイル単位の排他制御を備える。💋
"""

from __future__ import annotations

import logging
import os
import subprocess
import shutil
import re
import threading
from collections import defaultdict
from pathlib import Path

# 内部モジュールのインポート
from src.core.models import FileChange, FileAction
from src.core.git_tools import GitTool
from src.tools.terminal import TerminalOracle

log = logging.getLogger("ARK.Dock")

class Dock:
    """プロジェクトの実行環境を管理するドック。"""

    def __init__(self, workspace_root: Path, project_id: str):
        self.workspace_root = workspace_root
        self.project_id = project_id
        self.path = (workspace_root / project_id).resolve()
        self.git = GitTool(self.path)
        self.terminal = TerminalOracle(self.path)
        
        # 🌟 NEW: The Merge Protocol (衝突回避ロック機構)
        # ファイルパスごとの専用ロック（同時に同じファイルを触らせない）
        self._file_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        # パッケージインストールの全体ロック（同時にpip installを走らせない）
        self._pip_lock = threading.Lock()

    def setup_from_remote(self, repo_url: str) -> bool:
        """
        GitHub等からリポジトリを同期し、環境をセットアップする。
        ディレクトリが空でなくても（.venv等が先行して存在していても）強引にリモートと同期する。
        """
        log.info(f"⚓️ [Dock] Attempting to dock remote ship: {repo_url}")
        
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.path.mkdir(parents=True, exist_ok=True)

        if not (self.path / ".git").exists():
            log.info(f"🛰️ [Dock] Initializing and fetching from {repo_url}...")
            try:
                subprocess.run(["git", "init"], cwd=self.path, check=True, capture_output=True)
                self.git.setup_dock(repo_url)
                
                log.info("📥 [Dock] Fetching repository data...")
                subprocess.run(["git", "fetch", "origin"], cwd=self.path, check=True, capture_output=True)
                
                checkout_res = subprocess.run(["git", "checkout", "-f", "main"], cwd=self.path, capture_output=True)
                if checkout_res.returncode != 0:
                    subprocess.run(["git", "checkout", "-f", "master"], cwd=self.path, capture_output=True)
                
                subprocess.run(["git", "branch", "-M", "main"], cwd=self.path, capture_output=True)
                log.info(f"✅ [Dock] Remote repository synchronized perfectly.")
                
            except Exception as e:
                log.error(f"❌ [Dock] Failed to synchronize with remote: {e}")
                return False
        else:
            log.info("⚓️ [Dock] Repository already initialized. Pulling latest...")
            subprocess.run(["git", "pull", "origin", "main"], cwd=self.path, capture_output=True)

        self._ensure_venv()
        self.install_dependencies()

        clean_id = self.project_id.split('-')[-1]
        branch_name = f"ark/task-{clean_id}"
        self.git.create_topic_branch(branch_name)
        log.info(f"🌿 [Dock] Topic branch created/switched: {branch_name}")
        
        return True

    def _ensure_venv(self):
        """Pythonの仮想環境を構築する。"""
        venv_path = self.path / ".venv"
        if not venv_path.exists():
            log.info("🛡️ [Dock] Building shield (venv) for the ship...")
            cmd = "python3 -m venv .venv" if os.name != "nt" else "python -m venv .venv"
            subprocess.run(cmd.split(), cwd=self.path, capture_output=True)

    def install_dependencies(self):
        """requirements.txt をスキャンして依存関係をインストールする（スレッドセーフ）。"""
        # 🌟 UPDATE: 複数スレッドからの同時pip installを防ぐ排他ロック
        with self._pip_lock:
            req_file = self.path / "requirements.txt"
            if req_file.exists():
                log.info("📦 [Dock] Installing dependencies from requirements.txt...")
                venv_path = self.path / ".venv"
                pip_path = venv_path / "bin" / "pip" if os.name != "nt" else venv_path / "Scripts" / "pip.exe"
                
                self.terminal.execute_command(f"{pip_path} install -r requirements.txt")
                log.info("✅ [Dock] Dependency sync complete.")

    def write_artifacts(self, changes: list[FileChange]):
        """
        生成されたコードやパッチをファイルに書き込む（スレッドセーフ）。
        """
        needs_install = False
        for change in changes:
            target_path = self.path / change.path
            target_path_str = str(target_path.resolve())

            if change.path == "requirements.txt":
                needs_install = True

            # 🌟 UPDATE: The Merge Protocol - ファイルごとの排他ロックを取得
            with self._file_locks[target_path_str]:
                target_path.parent.mkdir(parents=True, exist_ok=True)

                if change.action == FileAction.UPDATE:
                    self._apply_patch(change, target_path)
                else:
                    target_path.write_text(change.content, encoding="utf-8")
                    log.info(f"📝 [Dock] File written safely (Locked): {change.path}")

        if needs_install:
            self.install_dependencies()

    def _apply_patch(self, change: FileChange, target_path: Path):
        """SEARCH/REPLACE 形式のパッチを適用する堅牢な外科手術エンジン。
        ※呼び出し元で既にファイルロックを取得している前提で動作します。"""
        if not target_path.exists():
            log.warning(f"⚠️ [Dock] Patch target not found: {change.path}. Creating instead.")
            target_path.write_text(self._clean_all_markers(change.content), encoding="utf-8")
            return

        source = target_path.read_text(encoding="utf-8")
        
        patch_pattern = re.compile(
            r"<{3,}\s*SEARCH[ \t]*\n(.*?)\n={3,}[ \t]*\n(.*?)\n>{3,}\s*REPLACE", 
            re.DOTALL | re.IGNORECASE
        )
        
        matches = patch_pattern.findall(change.content)
        
        if not matches:
            log.info(f"ℹ️ [Dock] No valid SEARCH/REPLACE blocks in {change.path}. Overwriting.")
            target_path.write_text(self._clean_all_markers(change.content), encoding="utf-8")
            return

        new_source = source
        success_count = 0
        
        for search_text, replace_text in matches:
            s_block = self._clean_block(search_text)
            r_block = self._clean_block(replace_text)

            if s_block in new_source:
                new_source = new_source.replace(s_block, r_block, 1)
                success_count += 1
            else:
                s_stripped = s_block.strip()
                if s_stripped and s_stripped in new_source:
                    new_source = new_source.replace(s_stripped, r_block.strip(), 1)
                    success_count += 1
                else:
                    log.warning(f"⚠️ [Dock] Patch mismatch in {change.path}. Search block not found.")
        
        if success_count > 0:
            target_path.write_text(new_source, encoding="utf-8")
            log.info(f"✅ [Dock] Surgically modified {change.path} ({success_count} blocks).")
        else:
            log.error(f"❌ [Dock] All patch blocks failed for {change.path}. Overwriting as fallback.")
            target_path.write_text(self._clean_all_markers(change.content), encoding="utf-8")

    def _clean_all_markers(self, content: str) -> str:
        """最終出力からすべてのパッチ用マーカーを掃除する。"""
        content = re.sub(r"<{3,}\s*SEARCH.*?\n", "", content, flags=re.IGNORECASE)
        content = re.sub(r"={3,}.*?\n", "", content)
        content = re.sub(r">{3,}\s*REPLACE.*?\n", "", content, flags=re.IGNORECASE)
        lines = content.split('\n')
        cleaned = [l for l in lines if not l.strip().startswith('```')]
        return '\n'.join(cleaned).strip()

    @staticmethod
    def _clean_block(block: str) -> str:
        """ブロック内に紛れ込んだマークダウンタグを除去する。"""
        lines = block.split('\n')
        cleaned = [l for l in lines if not l.strip().startswith('```')]
        return '\n'.join(cleaned)