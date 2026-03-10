"""
ARK — Git Tool (The Dock Engine)
================================
Git のローカル操作および GitHub API によるリモートリポジトリの自動生成を担当する。
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import requests

log = logging.getLogger("ARK.Git")

class GitTool:
    """Git 操作および GitHub 連携を行うクラス。"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.github_token = os.getenv("GITHUB_TOKEN")
        
        # Git ユーザー設定（環境変数から取得、なければデフォルト）
        self.user_name = os.getenv("GIT_AUTHOR_NAME", "ARK SYLPH")
        self.user_email = os.getenv("GIT_AUTHOR_EMAIL", "sylph@ark.local")

    def _run_git(self, args: list[str], cwd: Optional[Path] = None) -> bool:
        """Git コマンドを実行する内部ヘルパー。"""
        target_cwd = cwd or self.workspace
        try:
            # .git ディレクトリがない場合は自動で init 💋
            if not (target_cwd / ".git").exists() and args[0] != "init":
                log.info("Initializing new git repository in %s", target_cwd)
                subprocess.run(["git", "init"], cwd=target_cwd, check=True, capture_output=True)
                
            res = subprocess.run(
                ["git"] + args,
                cwd=target_cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            log.error("Git command failed: %s\nStderr: %s", " ".join(args), e.stderr)
            return False

    def create_remote_repo(self, name: str, description: str, private: bool = True) -> Optional[str]:
        """GitHub API を使用して新規リポジトリを生成する。"""
        if not self.github_token:
            log.warning("GITHUB_TOKEN が未設定です。リモート作成をスキップします。")
            return None

        log.info("🚀 Creating GitHub repository: %s", name)
        
        url = "https://api.github.com/user/repos"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "name": name,
            "description": description,
            "private": private,
            "auto_init": False 
        }

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 201:
                repo_data = response.json()
                log.info("✅ GitHub repository created: %s", repo_data.get("html_url"))
                return repo_data.get("clone_url")
            elif response.status_code == 422:
                log.warning("⚠️ Repository '%s' already exists. Fetching its URL...", name)
                # 👈 既存なら、ユーザー情報を取得してURLを推測・再構築するわ！
                user_res = requests.get("https://api.github.com/user", headers=headers)
                if user_res.status_code == 200:
                    username = user_res.json().get("login")
                    clone_url = f"https://github.com/{username}/{name}.git"
                    log.info("✅ Reusing existing repository: %s", clone_url)
                    return clone_url
                return None
            else:
                log.error("❌ GitHub API Error (%d): %s", response.status_code, response.text)
                return None
        except Exception as e:
            log.error("❌ GitHub API Request failed: %s", e)
            return None

    def setup_dock(self, repo_url: str):
        """リモートリポジトリを origin として設定する。"""
        log.info("🔗 Linking remote origin: %s", repo_url)
        # 既存のリモートをクリーンアップ
        subprocess.run(["git", "remote", "remove", "origin"], cwd=self.workspace, capture_output=True)
        self._run_git(["remote", "add", "origin", repo_url])
        self._run_git(["branch", "-M", "main"])

    def create_topic_branch(self, task_id: str) -> str:
        """タスク用のトピックブランチを作成する。"""
        branch_name = f"ark/task-{task_id[:8]}"
        log.info("🌿 Creating topic branch: %s", branch_name)
        self._run_git(["checkout", "-b", branch_name])
        return branch_name

    def commit(self, message: str) -> bool:
        """現在の変更をコミットする。"""
        self._run_git(["add", "."])
        self._run_git(["config", "user.name", self.user_name])
        self._run_git(["config", "user.email", self.user_email])
        
        log.info("💾 Committing changes: %s", message)
        return self._run_git(["commit", "-m", message])

    def push(self, branch_name: str):
        """リモートにプッシュする。"""
        log.info("🚀 Pushing branch %s to origin...", branch_name)
        # 最初のPushはリモートブランチがないのでエラーを無視して強制pushするオプションをつける
        self._run_git(["push", "-u", "origin", branch_name])