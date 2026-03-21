"""
ARK — GitHub Publisher
=======================================================================
Orchestrator の最終フェーズで、GitHub へのプッシュや
Pull Request の作成を専門に担当するモジュール。
"""

import os
import logging
import re
from typing import Optional
from src.core.dock import Dock

log = logging.getLogger("ARK.GitHubPublisher")

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
            
            # リポジトリ名のクレンジング (GitHub は英数字、ハイフン、アンダースコア、ドットのみ許可)
            raw_name = dock.path.name
            repo_name = re.sub(r'[^a-zA-Z0-9._-]', '-', raw_name)
            
            description = f"ARK Generated Project: {goal[:100]}"
            if len(goal) > 100:
                description += "..."
            
            # GitTool.create_remote_repo を呼び出し
            repo_url = dock.git.create_remote_repo(
                name=repo_name,
                description=description,
                private=True  # デフォルトはプライベート。公開したい場合はここを変えてね💋
            )
            
            if repo_url:
                dock.git.setup_dock(repo_url)
                log.info("✅ [Publisher] リモートリポジトリ '%s' とのリンクに成功したわ！", repo_name)
            else:
                # すでにリポジトリがある場合などは GitTool 側でログが出ているはず
                log.warning("⚠️ [Publisher] リモートの準備が完全ではないけれど、ローカル操作を続行するわね。")
        
        elif not is_url:
            log.info("⚓️ [Publisher] 既存の Git 構成を確認したわ。そのまま作業を進めるわね。")

        # 2. 作業用トピックブランチを作成
        branch_name = dock.git.create_topic_branch(task_id)

        # 3. リモートへ Push
        log.info("[Publisher] ブランチ '%s' をリモートに Push 中...", branch_name)
        if not dock.git.push(branch_name):
            log.warning("⚠️ [Publisher] Push に失敗したわ。リモートに書き込み権限があるか確認してちょうだい。")
            return None

        # 4. Pull Request の作成
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