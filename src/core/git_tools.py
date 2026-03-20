"""
ARK — Git Tool (The Dock Engine)
=======================================================================
Git のローカル操作およびリモートへの Push を担当する。
PR は自動作成せず、ユーザーがブラウザで作成しやすいように URL を案内する。
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

log = logging.getLogger("ARK.Git")

class GitTool:
    """Git 操作および GitHub 連携を行うクラス。"""

    def __init__(self, workspace_path: Path):
        """
        GitTool を初期化する。
        """
        self.workspace = workspace_path
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_url: Optional[str] = None
        
        # Git ユーザー設定
        self.user_name = os.getenv("GIT_AUTHOR_NAME", "ARK SYLPH")
        self.user_email = os.getenv("GIT_AUTHOR_EMAIL", "sylph@ark.local")

    def _run_git(self, args: list[str], cwd: Optional[Path] = None) -> bool:
        """Git コマンドを実行する内部メソッド。"""
        target_cwd = cwd or self.workspace
        try:
            is_init_or_clone = any(cmd in args for cmd in ["init", "clone"])
            if not (target_cwd / ".git").exists() and not is_init_or_clone:
                log.info("Initializing new git repository in %s", target_cwd)
                subprocess.run(["git", "init"], cwd=target_cwd, check=True, capture_output=True)
                
            subprocess.run(
                ["git"] + args,
                cwd=target_cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            token = self.github_token
            safe_args = [arg.replace(token, "***") if token else arg for arg in args]
            safe_stderr = e.stderr.replace(token, "***") if token and e.stderr else e.stderr
            log.error("Git command failed: %s\nStderr: %s", " ".join(safe_args), safe_stderr)
            return False

    def get_current_branch(self) -> str:
        """現在のブランチ名を取得する。"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"], 
                cwd=self.workspace, capture_output=True, text=True, check=True
            )
            name = result.stdout.strip()
            return name if name else "main"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "main"

    def setup_dock(self, repo_url: str):
        """リモートリポジトリ（origin）の設定を行う。"""
        log.info("🔗 Linking remote origin: %s", repo_url)
        subprocess.run(["git", "remote", "remove", "origin"], cwd=self.workspace, capture_output=True)
        
        auth_url = repo_url
        if self.github_token and repo_url.startswith("https://"):
            auth_url = repo_url.replace("https://", f"https://oauth2:{self.github_token}@")

        self._run_git(["remote", "add", "origin", auth_url])
        # 強制的に main にリネームするのは副作用があるため削除しました

    def commit_all(self, message: str) -> bool:
        """すべての変更をステージングし、コミットを実行する。"""
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.workspace, capture_output=True, text=True)
        if not status.stdout.strip():
            log.info("No changes to commit.")
            return True

        self._run_git(["add", "."])
        self._run_git(["config", "user.name", self.user_name])
        self._run_git(["config", "user.email", self.user_email])
        msg = message if message.strip() else "ARK Auto-commit"
        return self._run_git(["commit", "-m", msg])

    def create_topic_branch(self, task_id: str) -> str:
        """タスク識別子に基づいたトピックブランチを作成し、切り替える。"""
        prefix = "ark/task-"
        clean_id = task_id.replace(prefix, "").strip()
        branch_name = f"{prefix}{clean_id[:8]}"
        
        current_branch = self.get_current_branch()
        if current_branch == branch_name:
            log.info("Already on branch: %s", branch_name)
            return branch_name

        log.info("🌿 Switching to topic branch: %s", branch_name)
        if not self._run_git(["checkout", branch_name]):
            if not self._run_git(["checkout", "-b", branch_name]):
                log.error("Failed to create or switch to branch: %s", branch_name)
                return current_branch
        
        return branch_name

    def push(self, branch_name: str) -> bool:
        """指定したブランチをリモートリポジトリへ Push する。"""
        log.info("🚀 Pushing branch %s to origin...", branch_name)
        return self._run_git(["push", "-u", "origin", f"{branch_name}:{branch_name}", "--force"])

    def create_pull_request(self, branch_name: str, title: str, body: str) -> Optional[str]:
        """
        【変更点】自動作成をスキップし、ブラウザ用の PR 作成リンクをログに出力する。
        """
        try:
            res = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=self.workspace, capture_output=True, text=True)
            url = res.stdout.strip()
            if not url: return None
            
            url_core = url.split("github.com/")[-1].replace(".git", "")
            if "@" in url_core:
                url_core = url_core.split("@")[-1].split(":", 1)[-1]
            owner_repo = url_core
        except Exception:
            return None

        # GitHub の PR 比較画面の URL を生成
        pr_create_url = f"https://github.com/{owner_repo}/compare/main...{branch_name}?expand=1"
        
        log.info("==========================================================")
        log.info("🌟 Push completed successfully!")
        log.info("👉 To review and create a Pull Request, please click the link below:")
        log.info("🔗 %s", pr_create_url)
        log.info("==========================================================")

        return pr_create_url