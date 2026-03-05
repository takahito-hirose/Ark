from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("ARK.Tools")

def read_file(file_path: str | Path, workspace_path: str | Path | None = None) -> str:
    """
    指定されたファイルを安全に読み取ります。
    """
    # 👇 ここがミソ！ workspace_path が None ならカレントディレクトリを使うわ
    base_dir = workspace_path if workspace_path is not None else "."
    base = Path(base_dir).resolve()
    
    # あとはジェニーが書いてくれたコードで完璧！
    target = (base / Path(file_path)).resolve()

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