from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger("ARK.Git")

class GitStatus(NamedTuple):
    has_changes: bool
    branch: str

class GitTool:
    """
    ARK の自律的 Git バージョン管理をサポートするツール。
    """

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def _run_git(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        log.debug("Git Executing: git %s", " ".join(args))
        try:
            return subprocess.run(
                ["git", *args],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                errors="replace"
            )
        except subprocess.CalledProcessError as e:
            log.error("❌ Git failed: %s\nSTDOUT: %s\nSTDERR: %s", e, e.stdout, e.stderr)
            raise

    def get_status(self) -> GitStatus:
        """現在の変更状態とブランチ名を取得します。"""
        # porcelain 形式で変更を確認
        proc_status = self._run_git(["status", "--porcelain"])
        has_changes = bool(proc_status.stdout.strip())
        
        # 現在のブランチ名
        proc_branch = self._run_git(["branch", "--show-current"])
        branch = proc_branch.stdout.strip()
        
        return GitStatus(has_changes=has_changes, branch=branch)

    def create_topic_branch(self, task_id: str) -> str:
        """タスクIDに基づいた新しいトピックブランチを作成して移動します。"""
        branch_name = f"ark/task-{task_id[:8]}"
        log.info("Creating topic branch: %s", branch_name)
        try:
            # すでに存在する場合はチェックアウトのみ、なければ作成してチェックアウト
            self._run_git(["checkout", "-b", branch_name])
        except subprocess.CalledProcessError:
            log.warning("Branch %s already exists, checking out...", branch_name)
            self._run_git(["checkout", branch_name])
        return branch_name

    def commit(self, message: str) -> bool:
        """変更をステージングしてコミットします。"""
        # 全体を追加
        self._run_git(["add", "."])
        
        # 変更の有無を再度確認（Porcelain）
        status = self.get_status()
        if not status.has_changes:
            log.info("ℹ️ No changes to commit (skipping).")
            return False
            
        # コミット実行
        self._run_git(["commit", "-m", message])
        log.info("✅ Committed changes: %s", message)
        return True

    def push(self, branch_name: str) -> None:
        """リモートへプッシュします。"""
        log.info("Pushing branch %s to origin...", branch_name)
        # --set-upstream でプッシュ
        self._run_git(["push", "--set-upstream", "origin", branch_name])
        log.info("🚀 Pushed success: %s", branch_name)
