from __future__ import annotations

import logging
from pathlib import Path
from src.core.tools import read_file

log = logging.getLogger("ARK.AgentsCore")

def get_initial_context(workspace_path: Path) -> str:
    """
    ワークスペース内の既存ファイルから初期コンテキストを取得します。
    """
    context_parts = []
    # 主要な設定ファイルやREADME、既存のソースコードをスキャン
    # 今回はシンプルに、直下の README.md と main.py を対象とする（拡張可能）
    targets = ["README.md", "main.py", "requirements.txt"]
    
    for target in targets:
        content = read_file(target, workspace_path)
        if not content.startswith("Error:"):
            context_parts.append(f"### File: {target}\n```\n{content}\n```")
    
    if not context_parts:
        return "No existing context found in workspace."
    
    return "\n\n".join(context_parts)

def build_architect_prompt(goal: str, workspace_path: Path) -> str:
    """
    Architect 向けのプロンプトを構築します（初期コンテキスト付き）。
    """
    context = get_initial_context(workspace_path)
    
    return f"""\
あなたはARKフレームワークのArchitect SYLPHです。
ユーザーのゴールを分析し、実装計画（PlanPayload）を生成してください。

## ワークスペースの初期コンテキスト
{context}

## 出力フォーマット（厳守）
TARGET_FILES: <カンマ区切りのファイルパスリスト>
CONSTRAINTS: <カンマ区切りの制約リスト>
ACCEPTANCE: <カンマ区切りの受け入れ基準リスト>

## 制約
- ファイルパスは workspace/ からの相対パスで記述
- Python 3.11+ 対応コードを前提とする
- 型ヒントを必須とする

## ゴール
{goal}
"""

def build_coder_prompt(
    goal: str,
    target_files: list[str],
    constraints: list[str],
    acceptance: list[str],
    retry: int,
    workspace_path: Path,
    reviewer_feedback: str = ""
) -> str:
    """
    Coder 向けのプロンプトを構築します（初期コンテキスト付き）。
    """
    context = get_initial_context(workspace_path)
    
    feedback_section = ""
    if reviewer_feedback:
        feedback_section = f"\n## 前回のレビュー結果（修正必須）\n{reviewer_feedback}\n"

    return f"""\
あなたはARKフレームワークのCoder SYLPHです。
以下の実装計画に基づいてPythonコードを生成してください。

## ワークスペースの初期コンテキスト
{context}

## 出力フォーマット（厳守）
FILE: <ファイルパス>
```python
<生成するコード全体>
```

## 制約
- Python 3.11+ に準拠すること
- すべての関数・メソッドに型ヒントを付けること
- モジュールに docstring を付けること

## 実装計画
ゴール: {goal}
対象ファイル: {", ".join(target_files)}
制約: {", ".join(constraints)}
受け入れ基準: {", ".join(acceptance)}

## 試行回数
{retry}回目の実装（0が初回）
{feedback_section}
"""
