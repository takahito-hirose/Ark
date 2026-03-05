"""
ARK Phase 3 - File System Oracle Module
プロジェクトのディレクトリ構造の把握とファイル操作を担当するマイクロオラクル。
"""

import os
import logging
import sys

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FILE_SYSTEM_ORACLE_PROMPT = """
あなたは「File System Oracle」です。プロジェクトの空間把握とファイル操作に特化しています。
あなたの目的は、ユーザー（または他のエージェント）の要求に応じて、プロジェクトのディレクトリ構造を調査し、
適切なファイルを読み書きすることです。
推測でファイルパスを指定せず、必ず `get_tree` で構造を確認してから操作を行ってください。
"""

def get_tree(target_path: str, max_depth: int = 3) -> str:
    """指定されたディレクトリの構造をインデントされたツリー形式で返します。"""
    try:
        if not os.path.exists(target_path):
            return f"Error: Directory not found: {target_path}"

        lines = []
        base_path = os.path.abspath(target_path)
        exclude_dirs = {'.git', '__pycache__', '.venv', '.DS_Store', 'node_modules'}

        def _build_tree(current_dir: str, depth: int):
            if depth > max_depth:
                return

            try:
                entries = sorted(os.listdir(current_dir))
            except PermissionError:
                lines.append(f"{'    ' * depth}[Permission Denied: {os.path.basename(current_dir)}/]")
                return

            for entry in entries:
                if entry in exclude_dirs:
                    continue

                full_path = os.path.join(current_dir, entry)
                indent = "    " * depth
                
                if os.path.isdir(full_path):
                    lines.append(f"{indent}{entry}/")
                    _build_tree(full_path, depth + 1)
                else:
                    lines.append(f"{indent}{entry}")

        lines.append(f"{os.path.basename(base_path)}/")
        _build_tree(base_path, 1)
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error generating tree: {e}")
        return f"Error: {str(e)}"

def read_file(file_path: str) -> str:
    """指定されたファイルの内容を読み取ります。"""
    try:
        if not os.path.isfile(file_path):
            return f"Error: File not found: {file_path}"
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return f"Read error: {str(e)}"

def write_file(file_path: str, content: str) -> str:
    """指定されたファイルに内容を書き込みます。"""
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        msg = f"File written successfully: {file_path}"
        logger.info(msg)
        return msg
    except Exception as e:
        err_msg = f"Write error for {file_path}: {str(e)}"
        logger.error(err_msg)
        return err_msg

# --- CLI実行用のエントリーポイント ---
if __name__ == "__main__":
    # 実行例: python src/tools/file_system.py .
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(get_tree(target))