from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("ARK.Tools")

def read_file(file_path: str | Path, workspace_path: str | Path) -> str:
    """
    指定されたファイルを安全に読み取ります。
    
    workspace_path 配下のファイルのみアクセスを許可します（パス・トラバーサル対策）。
    
    Parameters
    ----------
    file_path : str | Path
        読み取るファイルのパス（相対パスを想定）。
    workspace_path : str | Path
        許可されるベースディレクトリ（ワークスペース）。

    Returns
    -------
    str
        ファイルの内容。エラー時は空文字列、またはエラーメッセージを返します。
    """
    base = Path(workspace_path).resolve()
    target = (base / Path(file_path)).resolve()

    # セキュリティチェック: ターゲットがベースディレクトリ内にあるか確認
    try:
        target.relative_to(base)
    except ValueError:
        log.error("🚫 Security Alert: Access denied to %s (outside workspace %s)", target, base)
        return "Error: Access denied (outside workspace)"

    if not target.is_file():
        log.warning("⚠️ File not found: %s", target)
        return f"Error: File not found: {file_path}"

    try:
        content = target.read_text(encoding="utf-8")
        log.info("✅ Read file: %s (%d bytes)", target, len(content))
        return content
    except Exception as e:
        log.error("❌ Failed to read file %s: %s", target, e)
        return f"Error: Failed to read file: {e}"
