"""
ARK Dock Management
===================
プロジェクトの作業ディレクトリ、ターミナル、Git操作、ファイル書き込み（外科手術）を
一手に引き受ける「造船所」クラス。
"""

import logging
from pathlib import Path

from src.core.models import FileChange
from src.tools.terminal import TerminalOracle
from src.core.git_tools import GitTool
from src.core.patch_engine import PatchEngine

log = logging.getLogger("ARK.Dock")

class Dock:
    def __init__(self, base_workspace: Path, project_id: str):
        # 1. ワークスペース（ドック）の作成
        self.path = base_workspace / project_id
        self.path.mkdir(parents=True, exist_ok=True)
        
        log.info("🏗️  Welcome to The Dock: %s", self.path)

        # 2. このドック専用のツールを準備
        self.terminal = TerminalOracle(workspace_path=self.path)
        self.git = GitTool(self.path)

    def write_artifacts(self, files: list[FileChange]) -> list[Path]:
        """
        生成されたコードをファイルに書き出すわ。
        パッチ形式なら外科手術、そうでなければ全上書きよ！💋
        """
        written_paths = []
        for fc in files:
            # ファイル名はフラットにドック直下に展開
            file_path = self.path / Path(fc.path).name
            content = fc.content

            if "<<<<<<< SEARCH" in content:
                # 🏥 外科手術（パッチ適用）
                success = PatchEngine.apply_patches(str(file_path), content)
                if success:
                    log.info("✅ Surgically modified: %s", fc.path)
                else:
                    log.warning("⚠️ Patch failed for %s. Overwriting instead.", fc.path)
                    file_path.write_text(content, encoding="utf-8")
            else:
                # 🆕 新規作成 or 全上書き
                file_path.write_text(content, encoding="utf-8")
                log.info("📝 File written: %s", fc.path)
            
            written_paths.append(file_path)
            
        return written_paths