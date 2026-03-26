"""
ARK — Git Tool (The Genesis Engine)
=======================================================================
初期化、コミット、プッシュの順序を完全に制御し、
新規・既存どちらのリポジトリでも安全にPushを行うわ💋
(Windows版curlのJSONエスケープ問題を回避するためurllibを使用し、
 GitHub APIの422エラー対策として制御文字をサニタイズします)
"""

import logging
import os
import subprocess
import json
import urllib.request
import urllib.error
import re
from pathlib import Path
from typing import Optional

log = logging.getLogger("ARK.Git")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class GitTool:
    """Git 操作および GitHub 連携を行うクラス。"""

    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_url: Optional[str] = None
        self.user_name = os.getenv("GIT_AUTHOR_NAME", "ARK SYLPH")
        self.user_email = os.getenv("GIT_AUTHOR_EMAIL", "sylph@ark.local")

        if self.github_token:
            self.github_token = self.github_token.strip()

    def _run_git(self, args: list[str], cwd: Optional[Path] = None, silent: bool = False) -> bool:
        """Git コマンドを実行。必要に応じて init するわ。"""
        target_cwd = cwd or self.workspace
        
        if not (target_cwd / ".git").exists() and "init" not in args:
            log.info("🐣 Git repository missing. Initializing now...")
            subprocess.run(["git", "init", "-b", "main"], cwd=target_cwd, capture_output=True)

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
        self.repo_url = repo_url  
        
        self._run_git(["rev-parse", "--is-inside-work-tree"], silent=True)
        subprocess.run(["git", "remote", "remove", "origin"], cwd=self.workspace, capture_output=True)
        
        auth_url = repo_url
        if self.github_token and repo_url.startswith("https://"):
            auth_url = repo_url.replace("https://", f"https://{self.github_token}@")
        
        log.info("🔗 Setting remote origin to %s", repo_url)
        self._run_git(["remote", "add", "origin", auth_url])

    def _ensure_auth_url(self):
        """リモートURLに魔法の鍵（トークン）がなければ確実に注入する防衛機構💋"""
        if not self.github_token:
            return

        res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=self.workspace, capture_output=True, text=True)
        current_url = res.stdout.strip()

        if current_url and current_url.startswith("https://") and "@" not in current_url:
            auth_url = current_url.replace("https://", f"https://{self.github_token}@")
            subprocess.run(["git", "remote", "set-url", "origin", auth_url], cwd=self.workspace)
            log.info("🔐 [GitTool] Injected magic key into existing remote origin URL.")

    def commit_all(self, message: str) -> bool:
        """確実に歴史（コミット）を作るわよ💋"""
        self._run_git(["config", "user.name", self.user_name])
        self._run_git(["config", "user.email", self.user_email])
        self._run_git(["add", "."])
        
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.workspace, capture_output=True, text=True)
        if status.stdout.strip():
            return self._run_git(["commit", "-m", message])
        
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.workspace, capture_output=True)
        if res.returncode != 0:
            log.info("📜 Creating initial empty commit to stabilize the branch.")
            return self._run_git(["commit", "--allow-empty", "-m", "Initial Genesis Commit by ARK 💋"])
            
        return True

    def create_topic_branch(self, task_id: str) -> str:
        """ブランチを作成。まずは歴史があることを確認するわ。"""
        self.commit_all("Auto-stabilize before branching 💋")
        branch_name = f"ark/task-{task_id[:8]}"
        log.info("🌿 Switching to branch: %s", branch_name)
        
        if self._run_git(["checkout", "-B", branch_name]):
            return branch_name
        return "main"

    def push(self, branch_name: str) -> bool:
        """Push を実行。HEAD:branch_name 形式で確実に送るわ💋"""
        log.info("🚢 Pushing %s to origin...", branch_name)
        
        res = subprocess.run(["git", "remote"], cwd=self.workspace, capture_output=True, text=True)
        if "origin" not in res.stdout:
            if self.repo_url:
                log.info("🩹 Origin is missing, but repo_url is known. Auto-setting up dock...")
                self.setup_dock(self.repo_url)
            else:
                log.error("❌ Remote 'origin' is missing and repo_url is unknown. Skipping push.")
                return False
            
        self._ensure_auth_url()
            
        return self._run_git(["push", "-u", "origin", f"HEAD:{branch_name}", "--force"])

    def create_remote_repo(self, name: str, description: str = "", private: bool = True, **kwargs) -> Optional[str]:
        """GitHub API でリモートリポジトリを作成 (urllib版)。"""
        if not self.github_token:
            log.error("❌ GITHUB_TOKEN is missing.")
            return None

        # 🌟 NEW: 改行などの制御文字(\x00-\x1f)を半角スペースに置換してサニタイズ
        safe_description = re.sub(r'[\x00-\x1f\x7f]', ' ', description).strip()

        log.info("🏗️ Creating remote GitHub repository: %s", name)
        payload = {"name": name, "description": safe_description, "private": private}
        payload.update(kwargs)

        url = "https://api.github.com/user/repos"
        headers = {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                if "clone_url" in resp_data:
                    self.repo_url = resp_data["clone_url"]
                    return resp_data["clone_url"]
                return None
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            log.error("❌ GitHub API HTTP Error %s: %s\nDetails: %s", e.code, e.reason, error_body)
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