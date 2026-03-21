"""
ARK — Git Tool (The Genesis Engine)
=======================================================================
初期化、コミット、プッシュの順序を完全に制御し、
「歴史のないリポジトリ」によるプッシュエラーを撲滅するわ💋
"""

import logging
import os
import subprocess
import json
from pathlib import Path
from typing import Optional

log = logging.getLogger("ARK.Git")

class GitTool:
    """Git 操作および GitHub 連携を行うクラス。"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_url: Optional[str] = None
        self.user_name = os.getenv("GIT_AUTHOR_NAME", "ARK SYLPH")
        self.user_email = os.getenv("GIT_AUTHOR_EMAIL", "sylph@ark.local")

    def _run_git(self, args: list[str], cwd: Optional[Path] = None, silent: bool = False) -> bool:
        """Git コマンドを実行。必要に応じて init するわ。"""
        target_cwd = cwd or self.workspace
        
        # .git がない場合は即座に初期化
        if not (target_cwd / ".git").exists() and "init" not in args:
            log.info("🐣 Git repository missing. Initializing now...")
            subprocess.run(["git", "init"], cwd=target_cwd, capture_output=True)
            subprocess.run(["git", "checkout", "-b", "main"], cwd=target_cwd, capture_output=True)

        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=target_cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            if not silent:
                token = self.github_token
                safe_stderr = e.stderr.replace(token, "***") if token and e.stderr else e.stderr
                log.error("Git command failed: %s\nStderr: %s", " ".join(args), safe_stderr)
            return False

    def setup_dock(self, repo_url: str):
        """リモート origin を設定。"""
        # 強制的に初期化を走らせるためにダミーのgitコマンドを叩く
        self._run_git(["rev-parse", "--is-inside-work-tree"], silent=True)
        
        subprocess.run(["git", "remote", "remove", "origin"], cwd=self.workspace, capture_output=True)
        
        auth_url = repo_url
        if self.github_token and repo_url.startswith("https://"):
            auth_url = repo_url.replace("https://", f"https://oauth2:{self.github_token}@")
        
        log.info("🔗 Setting remote origin to %s", repo_url)
        self._run_git(["remote", "add", "origin", auth_url])

    def commit_all(self, message: str) -> bool:
        """確実に歴史（コミット）を作るわよ💋"""
        self._run_git(["config", "user.name", self.user_name])
        self._run_git(["config", "user.email", self.user_email])
        self._run_git(["add", "."])
        
        # 変更があるか確認
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.workspace, capture_output=True, text=True)
        if status.stdout.strip():
            return self._run_git(["commit", "-m", message])
        
        # 歴史が全くない（HEADがない）場合は、空コミットを強制する
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.workspace, capture_output=True)
        if res.returncode != 0:
            log.info("📜 Creating initial empty commit to stabilize the branch.")
            return self._run_git(["commit", "--allow-empty", "-m", "Initial Genesis Commit by ARK 💋"])
            
        return True

    def create_topic_branch(self, task_id: str) -> str:
        """ブランチを作成。まずは歴史があることを確認するわ。"""
        # 念のためコミットを試みる（歴史がないとブランチが作れないから）
        self.commit_all("Auto-stabilize before branching 💋")
        
        branch_name = f"ark/task-{task_id[:8]}"
        log.info("🌿 Switching to branch: %s", branch_name)
        
        if self._run_git(["checkout", "-B", branch_name]):
            return branch_name
        return "main"

    def push(self, branch_name: str) -> bool:
        """Push を実行。HEAD:branch_name 形式で確実に送るわ💋"""
        log.info("🚀 Pushing %s to origin...", branch_name)
        
        # origin があるか最終確認
        res = subprocess.run(["git", "remote"], cwd=self.workspace, capture_output=True, text=True)
        if "origin" not in res.stdout:
            log.error("❌ Remote 'origin' is missing. Skipping push.")
            return False
            
        # 確実に現在のコミット(HEAD)をリモートに叩き込む
        return self._run_git(["push", "-u", "origin", f"HEAD:{branch_name}", "--force"])

    def create_remote_repo(self, name: str, description: str = "", private: bool = True, **kwargs) -> Optional[str]:
        """GitHub API でリモートリポジトリを作成。"""
        if not self.github_token:
            log.error("❌ GITHUB_TOKEN is missing.")
            return None

        log.info("🏗️ Creating remote GitHub repository: %s", name)
        payload = {"name": name, "description": description, "private": private}
        payload.update(kwargs)

        cmd = [
            "curl", "-s", "-X", "POST",
            "-H", f"Authorization: token {self.github_token}",
            "-H", "Accept: application/vnd.github.v3+json",
            "-d", json.dumps(payload),
            "https://api.github.com/user/repos"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            response = json.loads(result.stdout)
            if "clone_url" in response:
                return response["clone_url"]
            else:
                log.error("❌ GitHub API Error: %s", response.get("message"))
                return None
        except Exception as e:
            log.error("❌ API Request failed: %s", e)
            return None

    def create_pull_request(self, branch_name: str, title: str, body: str) -> Optional[str]:
        """PR 比較URLを生成。"""
        res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=self.workspace, capture_output=True, text=True)
        raw_url = res.stdout.strip()
        if not raw_url: return None
        
        clean_url = raw_url.replace(".git", "").split("@")[-1].replace(":", "/")
        if not clean_url.startswith("http"): clean_url = "https://" + clean_url
        
        return f"{clean_url}/compare/main...{branch_name}?expand=1"