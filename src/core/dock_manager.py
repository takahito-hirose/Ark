"""
ARK Dock Manager
=======================================================================
ターゲットが URL かローカルパスかを判定し、適切な Dock（接岸領域）を
準備・初期化する役割を担うモジュール。
"""

import logging
from pathlib import Path
from typing import Optional
from src.core.dock import Dock

log = logging.getLogger("ARK.DockManager")

def setup_dock(
    target_input: str, 
    base_workspace: Path, 
    task_id: str, 
    plan_project_name: Optional[str] = None
) -> Dock:
    """
    ターゲット入力に基づいて Dock をセットアップし、返却するわよ。💋
    """
    # 1. URL かどうかの判定
    is_url = target_input.startswith(("http://", "https://", "git@"))

    # 2. クローンモード (リモートリポジトリ)
    if is_url:
        project_id = f"cloned-{task_id[:8]}"
        dock = Dock(base_workspace / "docks", project_id)
        if not dock.setup_from_remote(target_input):
            raise RuntimeError("⚓️ Remote docking failed: リポジトリのクローンに失敗したわ。")
        log.info("⚓️ CLONE MODE: リポジトリを %s にクローンしたよ！", dock.path)
        return dock

    # 3. アップデートモード (既存のローカルパス)
    target_path = Path(target_input).resolve() if target_input else None
    if target_path and target_path.exists():
        log.info("🔌 UPDATE MODE: 既存のプロジェクト %s をマウントするね。", target_path)
        return Dock(target_path.parent, target_path.name)

    # 4. 新規造船モード
    project_id = plan_project_name or f"ark-project-{task_id[:8]}"
    dock = Dock(base_workspace, project_id)
    log.info("🏗️ NEW PROJECT MODE: 新しいドック %s を建造するわ！", dock.path)
    return dock