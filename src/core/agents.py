"""
ARK — Core Context Helpers (Phase 15 Edition)
=====================================================
ワークスペースのコンテキスト（ファイルツリーや初期コード）を
エージェント向けにフォーマットするユーティリティ群だよ💋
※プロンプト本文は各エージェントの `Skills.md` に分離されました！
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from src.core.tools import read_file

log = logging.getLogger("ARK.ContextHelpers")

def get_initial_context(workspace_path: Path, targets: list[str] | None = None) -> str:
    """
    ワークスペース内の既存ファイルから初期コンテキストを取得します。
    """
    if targets is None:
        targets = ["README.md", "main.py", "requirements.txt"]
        
    context_parts = []
    
    for target in targets:
        clean_target = Path(target).name
        content = read_file(clean_target, workspace_path)
        if not content.startswith("Error:"):
            context_parts.append(f"### File: {clean_target}\n```python\n{content}\n```")
    
    if not context_parts:
        return "No existing context found in workspace."
    
    return "\n\n".join(context_parts)

def get_file_tree(workspace_path: Path) -> str:
    """
    ワークスペース内のファイル構造をスキャンして、LLMが理解しやすいツリー形式で返します。
    """
    lines = []
    ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".ark_memory"}
    
    if not workspace_path or not workspace_path.exists():
        return "No files found (Empty Workspace)."

    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith("ark-project-")]
            
            rel_path = os.path.relpath(root, workspace_path)
            depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
            indent = "  " * depth
            
            folder_name = os.path.basename(root) if rel_path != "." else "root"
            lines.append(f"{indent}[Dir] {folder_name}/")
            
            sub_indent = "  " * (depth + 1)
            for f in files:
                if not f.startswith("."):
                    lines.append(f"{sub_indent}- {f}")
    except Exception as e:
        return f"Error scanning workspace: {e}"
        
    return "\n".join(lines) if lines else "No files found."