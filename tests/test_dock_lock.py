"""
ARK — Dock Stress Test
======================
複数のスレッドから同時に同じファイルへ書き込み・パッチ適用を行い、
The Merge Protocol が正しく動作するかを検証します。
"""

import threading
import time
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加して src をインポート可能にする
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from src.core.dock import Dock
from src.core.models import FileChange, FileAction

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(threadName)s: %(message)s'
)
log = logging.getLogger("ARK.Test")

def simulate_coder_work(dock: Dock, coder_id: int, file_path: str):
    """個別のコーダーがファイルを書き換えるシミュレーション"""
    log.info(f"👷 Coder-{coder_id} が作業を開始しました。")
    
    # SEARCH/REPLACE パッチの作成
    # 実際にはもっと複雑ですが、ここでは単純な追記を試みます
    change = FileChange(
        path=file_path,
        action=FileAction.UPDATE,
        content=f"""
<<<< SEARCH
# Initial Content
====
# Content modified by Coder-{coder_id}
>>>> REPLACE
"""
    )
    
    try:
        # 書き込み実行（ここでロックが発生します）
        dock.write_artifacts([change])
        log.info(f"✅ Coder-{coder_id} が書き込みを完了しました。")
    except Exception as e:
        log.error(f"❌ Coder-{coder_id} が失敗しました: {e}")

def run_stress_test():
    # テスト用のワークスペース設定
    workspace = Path("./test_workspace")
    project_id = "test-ship"
    dock = Dock(workspace, project_id)
    
    # テスト用ファイルの初期化
    test_file_name = "main.py"
    target_file = dock.path / test_file_name
    dock.path.mkdir(parents=True, exist_ok=True)
    target_file.write_text("# Initial Content\n", encoding="utf-8")
    
    log.info("🔥 ストレステストを開始します。5つのスレッドが同時に書き込みを試みます。")
    
    threads = []
    for i in range(5):
        t = threading.Thread(
            target=simulate_coder_work, 
            args=(dock, i, test_file_name),
            name=f"Worker-{i}"
        )
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()

    # 最終的なファイル内容を確認
    final_content = target_file.read_text()
    log.info("--- 最終的なファイル内容 ---")
    log.info("\n" + final_content)
    log.info("----------------------------")
    log.info("テストが完了しました。ロックにより競合が回避されていれば成功です。")

if __name__ == "__main__":
    run_stress_test()