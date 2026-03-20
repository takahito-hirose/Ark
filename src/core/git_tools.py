"""
ARK — Git Tool (The Dock Engine)
================================
Git のローカル操作および GitHub API によるリモートリポジトリの自動生成・PR作成を担当する。
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
        self.repo_url: Optional[str] = None
        
        # Git ユーザー設定
        self.user_name = os.getenv("GIT_AUTHOR_NAME", "ARK SYLPH")
        self.user_email = os.getenv("GIT_AUTHOR_EMAIL", "sylph@ark.local")

    def _run_git(self, args: list[str], cwd: Optional[Path] = None) -> bool:
        target_cwd = cwd or self.workspace
        try:
            if not (target_cwd / ".git").exists() and args[0] != "init":
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
            safe_args = [arg.replace(self.github_token, "***") if self.github_token else arg for arg in args]
            safe_stderr = e.stderr.replace(self.github_token, "***") if self.github_token and e.stderr else e.stderr
            log.error("Git command failed: %s\nStderr: %s", " ".join(safe_args), safe_stderr)
            return False

    def get_current_branch(self) -> str:
        """現在のブランチ名を取得するわよ💋"""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"], 
                cwd=self.workspace, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "main"

    def create_remote_repo(self, name: str, description: str, private: bool = True) -> Optional[str]:
        if not self.github_token:
            return None

        log.info("🚀 Creating GitHub repository: %s", name)
        url = "https://api.github.com/user/repos"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        safe_description = " ".join(description.splitlines()).strip()
        if len(safe_description) > 200:
            safe_description = safe_description[:197] + "..."

        data = {"name": name, "description": safe_description, "private": private, "auto_init": False}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=10)
            if response.status_code == 201:
                repo_data = response.json()
                self.repo_url = repo_data.get("html_url")
                return repo_data.get("clone_url")
            elif response.status_code == 422:
                user_res = requests.get("https://api.github.com/user", headers=headers)
                if user_res.status_code == 200:
                    username = user_res.json().get("login")
                    clone_url = f"https://github.com/{username}/{name}.git"
                    self.repo_url = f"https://github.com/{username}/{name}"
                    return clone_url
                return None
        except Exception as e:
            log.error("❌ GitHub API Request failed: %s", e)
            return None
        return None

    def setup_dock(self, repo_url: str):
        log.info("🔗 Linking remote origin: %s", repo_url)
        subprocess.run(["git", "remote", "remove", "origin"], cwd=self.workspace, capture_output=True)
        
        auth_url = repo_url
        if self.github_token and repo_url.startswith("https://"):
            auth_url = repo_url.replace("https://", f"https://oauth2:{self.github_token}@")

        self._run_git(["remote", "add", "origin", auth_url])
        self._run_git(["branch", "-M", "main"])

    def commit(self, message: str) -> bool:
        """コミット処理。mainブランチを汚さないよう自動退避するわ！💋"""
        current_branch = self.get_current_branch()

        # 🚨 main や master にいる場合は、勝手にコミットしないように保護！
        if current_branch in ["main", "master"]:
            import uuid
            safe_branch = f"ark/update-{str(uuid.uuid4())[:8]}"
            log.info("🛡️ Protecting %s branch! Evacuating to: %s", current_branch, safe_branch)
            self._run_git(["checkout", "-b", safe_branch])

        self._run_git(["add", "."])
        self._run_git(["config", "user.name", self.user_name])
        self._run_git(["config", "user.email", self.user_email])
        return self._run_git(["commit", "-m", message])

    def create_topic_branch(self, task_id: str) -> str:
        """作業用ブランチを作成（またはリネーム）するわよ💋"""
        branch_name = f"ark/task-{task_id[:8]}"
        current_branch = self.get_current_branch()

        if current_branch == branch_name:
            return branch_name
            
        # commit時に自動生成された ark/update-xxx ブランチにいるなら、それをタスクIDのブランチ名にリネームする
        if current_branch.startswith("ark/update-"):
            log.info("🔄 Renaming temp branch %s to %s", current_branch, branch_name)
            self._run_git(["branch", "-m", branch_name])
            return branch_name

        # それ以外なら新しく切る
        log.info("🌿 Creating new topic branch: %s", branch_name)
        self._run_git(["checkout", "-b", branch_name])
        return branch_name

    def push(self, branch_name: str):
        log.info("🚀 Pushing branch %s to origin...", branch_name)
        self._run_git(["push", "-u", "origin", branch_name])

    def create_pull_request(self, branch_name: str, title: str, body: str) -> Optional[str]:
        """GitHub APIを叩いてPull Requestを自動作成するわよ！💋"""
        if not self.github_token:
            log.warning("⚠️ No GITHUB_TOKEN. Skipping PR creation.")
            return None

        # リモートURLから owner/repo を抽出
        try:
            res = subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=self.workspace, capture_output=True, text=True)
            url = res.stdout.strip()
            if not url: return None
            
            # URLのパース
            url = url.replace("https://github.com/", "").replace(".git", "")
            if "oauth2:" in url:
                url = url.split("@")[-1].replace("github.com/", "")
            
            owner_repo = url
        except Exception:
            return None

        log.info("📝 Creating Pull Request for %s...", owner_repo)
        api_url = f"https://api.github.com/repos/{owner_repo}/pulls"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "title": title,
            "head": branch_name,
            "base": "main",  # ターゲットは常にmainを想定
            "body": body
        }

        try:
            response = requests.post(api_url, json=data, headers=headers, timeout=10)
            if response.status_code == 201:
                pr_url = response.json().get("html_url")
                log.info("✅ Pull Request created successfully: %s", pr_url)
                return pr_url
            else:
                log.error("❌ PR Creation failed: %s - %s", response.status_code, response.text)
                return None
        except Exception as e:
            log.error("❌ Error creating PR: %s", e)
            return None