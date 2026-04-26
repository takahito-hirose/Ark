"""
ARK — GitHub Publisher
=======================================================================
Orchestrator の最終フェーズで、GitHub へのプッシュや
Pull Request の作成を専門に担当するモジュール。
"""

import os
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional
from src.core.dock import Dock

log = logging.getLogger("ARK.GitHubPublisher")

def deploy_pharos_defense(dock: Dock):
    """
    The Pharosの防衛網（YAMLとSecret）をターゲットリポジトリに自動配備する。
    ARKが触れたすべてのリポジトリをThe Pharosの監視下に置くためのプロトコル。
    """
    workspace_path = dock.path
    
    # 1. YAMLファイルの自動配備
    github_dir = workspace_path / ".github" / "workflows"
    github_dir.mkdir(parents=True, exist_ok=True)
    
    yaml_path = github_dir / "pharos-audit.yml"
    if not yaml_path.exists():
        log.info("🗼 [Publisher] Deploying The Pharos workflow to target repository...")
        yaml_content = """name: 🗼 The Pharos Code Audit

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - name: 🚢 Checkout Repository
        uses: actions/checkout@v4
        
      - name: 🗼 Run The Pharos Audit
        uses: takahito-hirose/The-Pharos@main
        with:
          gemini_api_key: ${{ secrets.GOOGLE_API_KEY }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
"""
        yaml_path.write_text(yaml_content, encoding="utf-8")
        
        # Gitに追加してコミット
        try:
            subprocess.run(["git", "add", ".github/"], cwd=workspace_path, check=True)
            result = subprocess.run(
                ["git", "commit", "-m", "chore: deploy The Pharos absolute defense [skip ci]"], 
                cwd=workspace_path, capture_output=True, text=True
            )
            if result.returncode == 0:
                log.info("✅ [Publisher] The Pharos workflow committed successfully.")
        except Exception as e:
            log.warning("⚠️ [Publisher] Failed to commit Pharos workflow: %s", e)

    # 2. Secretの自動登録 (gh CLI を使用)
    # ARKが使っているAPIキーを、そのまま対象リポジトリのGitHub Secretsに注入する
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        log.info("🔐 [Publisher] Injecting Secret (GOOGLE_API_KEY) to remote repository...")
        try:
            # cwdを指定することで、origin URLから対象リポジトリをghコマンドが自動判別する
            subprocess.run(
                ["gh", "secret", "set", "GOOGLE_API_KEY", "--body", api_key],
                cwd=workspace_path, check=True, capture_output=True, text=True
            )
            log.info("✅ [Publisher] Secret successfully injected into remote!")
        except subprocess.CalledProcessError as e:
            log.warning("⚠️ [Publisher] Failed to set secret: %s", e.stderr)
        except Exception as e:
            log.warning("⚠️ [Publisher] Error setting secret via gh CLI: %s", e)
    else:
        log.warning("⚠️ [Publisher] GOOGLE_API_KEY not found in local environment. Skipping Secret injection.")


def publish_to_github(
    dock: Dock, 
    task_id: str, 
    goal: str, 
    is_new_project: bool, 
    is_url: bool
) -> Optional[str]:
    """
    リモートリポジトリの作成、ブランチの Push、PR の作成を実行する。
    成功した場合は、作成された Pull Request の URL を返す。

    Args:
        dock (Dock): 実行中のプロジェクトドック環境。
        task_id (str): タスクの一意識別子。
        goal (str): ユーザーが設定した最終目標。
        is_new_project (bool): 新規リポジトリ作成が必要かどうかのフラグ。
        is_url (bool): ターゲットが既にリモートURLであるか。

    Returns:
        Optional[str]: 成功時は PR の URL、失敗またはスキップ時は None。
    """
    # トークンや Git コンポーネントの存在を確認
    github_token = os.getenv("GITHUB_TOKEN")
    if not dock or not dock.git or not github_token:
        log.info("⚠️ [Publisher] GITHUB_TOKEN が未設定、または Git が未初期化のためパブリッシュをスキップします。")
        return None

    try:
        # 1. 新規プロジェクトの場合は GitHub 上にリモートリポジトリを作成
        if is_new_project:
            log.info("🏗️ [Publisher] GitHub に新規リモートリポジトリを建造中...")
            
            # リポジトリ名のクレンジング
            raw_name = dock.path.name
            repo_name = re.sub(r'[^a-zA-Z0-9._-]', '-', raw_name)
            
            description = f"ARK Generated Project: {goal[:100]}"
            if len(goal) > 100:
                description += "..."
            
            repo_url = dock.git.create_remote_repo(
                name=repo_name,
                description=description,
                private=True
            )
            
            if repo_url:
                dock.git.setup_dock(repo_url)
                log.info("✅ [Publisher] リモートリポジトリ '%s' とのリンクに成功したわ！", repo_name)
            else:
                log.warning("⚠️ [Publisher] リモートの準備が完全ではないけれど、ローカル操作を続行するわね。")
        
        elif not is_url:
            log.info("⚓️ [Publisher] 既存の Git 構成を確認したわ。そのまま作業を進めるわね。")

        # 2. 作業用トピックブランチを作成
        branch_name = dock.git.create_topic_branch(task_id)

        # --- 🌟 NEW: The Pharos 防衛網の自動配備（YAML生成とSecret注入） ---
        deploy_pharos_defense(dock)
        # -----------------------------------------------------------------

        # 3. Push前にリモートURLへ魔法の鍵(TOKEN)を強制注入
        try:
            log.info("🔐 [Publisher] Gitの認証バイパス処理を実行中...")
            # 現在の origin URL を取得
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=dock.path, capture_output=True, text=True
            )
            origin_url = result.stdout.strip()

            # URLにトークンが含まれていなければ埋め込む
            if origin_url and origin_url.startswith("https://") and "@" not in origin_url:
                auth_url = origin_url.replace("https://", f"https://{github_token}@")
                subprocess.run(
                    ["git", "remote", "set-url", "origin", auth_url],
                    cwd=dock.path, check=True
                )
                log.info("✅ [Publisher] リモートURLに魔法の鍵をセットアップ完了！")
        except Exception as e:
            log.warning("⚠️ [Publisher] 認証URLのセットアップ中に問題発生: %s", e)

        # 4. リモートへ Push
        log.info("[Publisher] ブランチ '%s' をリモートに Push 中...", branch_name)
        if not dock.git.push(branch_name):
            log.warning("⚠️ [Publisher] Push に失敗したわ。リモートに書き込み権限があるか確認してちょうだい。")
            return None

        # 5. Pull Request の作成
        pr_title = f"ARK Update: {goal[:60]}"
        if len(goal) > 60:
            pr_title += "..."
            
        pr_body = (
            f"## ARK Autonomous Update 🚢\n\n"
            f"**Mission Goal:**\n> {goal}\n\n"
            f"**Task ID:** `{task_id}`\n\n"
            f"---\n"
            f"*Generated with ❤️ by ARK (Autonomous Resilient Kernel)*"
        )
        
        pr_url = dock.git.create_pull_request(
            branch_name=branch_name, 
            title=pr_title, 
            body=pr_body
        )
        
        if pr_url:
            log.info("🎉 [Publisher] Pull Request が完成したわ！ URL: %s", pr_url)
            return pr_url
        else:
            log.warning("⚠️ [Publisher] PR リンクの生成に失敗したわ。でも Push は成功してるから安心して！")

    except Exception as e:
        log.error("❌ [Publisher] パブリッシュ処理中に予期せぬエラーが発生したわ: %s", e)

    return None