from __future__ import annotations

import logging
from pathlib import Path
from src.core.tools import read_file
from src.core.models import ExecutionAttempt

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

def build_remediation_prompt(
    goal: str,
    target_files: list[str],
    retry: int,
    workspace_path: Path,
    failure_reason: str,
    stacktrace: str,
    current_source: str,
    attempt_history: list[ExecutionAttempt] | None = None
) -> str:
    """
    実行エラーが発生した際の修正用プロンプトを構築します。
    過去の失敗履歴（Short-Term Memory）を含めます。
    """
    context = get_initial_context(workspace_path)
    
    history_section = ""
    if attempt_history:
        history_section = "\n## これまでの試行履歴（失敗の記録）\n"
        for i, attempt in enumerate(attempt_history, 1):
            history_section += f"""
### 試行 {i}
- **エラー**: 
```
{attempt.error[:500]}{"..." if len(attempt.error) > 500 else ""}
```
- **試したコード**:
```python
{attempt.code[:1000]}{"..." if len(attempt.code) > 1000 else ""}
```
---
"""

    return f"""\
あなたはARKフレームワークのCoder SYLPHです。
直前のコード実行でエラーが発生しました。提供されたスタックトレースおよび【これまでの試行履歴】を詳細に分析し、問題を修正した完全なコードを再生成してください。

## ワークスペースの初期コンテキスト
{context}

## 直近の実行エラー情報
- **Failure Reason**: {failure_reason}
- **Stacktrace**:
```
{stacktrace}
```

## 現在のソースコード
{current_source}
{history_section}

## ⚠️ 重要：セルフヒーリング制約
これまでの失敗履歴を分析し、**既に試して失敗したアプローチを絶対に繰り返さないこと**。
履歴から根本原因を推測し、必要であれば設計を見直し、全く新しいアプローチでコードを修正してください。

## 出力フォーマット（厳守）
FILE: <ファイルパス>
```python
<修正後のコード全体>
```

## 実装計画（再確認）
ゴール: {goal}
対象ファイル: {", ".join(target_files)}

## 試行回数
{retry}回目の修正試行（セルフヒーリング）
"""

def build_commit_msg_prompt(goal: str, files: list[str]) -> str:
    """
    今回の変更内容を要約し、Conventional Commits 形式のメッセージを生成します。
    """
    return f"""\
あなたはARKフレームワークのCoder SYLPHです。
以下の実装結果を要約し、Gitのコミットメッセージ（1行）を生成してください。

## ゴール
{goal}

## 変更されたファイル
{", ".join(files)}

## 制約（厳守）
- 形式: <type>: <description>
- type: fix, feat, docs, style, refactor, test, chore
- 英語で記述すること。
- 50文字以内。
- 本文等は含まず、メッセージ1行のみを出力すること。

## 出力例
feat: implement short-term memory logic
fix: handle port conflict in web server
"""
