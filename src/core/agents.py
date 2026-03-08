"""
ARK — Agents Prompt Core
=========================
各エージェント向けのシステムプロンプトおよび命令文を構築するロジック。
Phase 4-B 以降の「責務の分離」に基づき、Reflector 向けのプロンプトを追加。
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from src.core.tools import read_file
from src.core.models import ExecutionAttempt

log = logging.getLogger("ARK.AgentsCore")

# ---------------------------------------------------------------------------
# Shared Context Helpers
# ---------------------------------------------------------------------------

def get_initial_context(workspace_path: Path) -> str:
    """
    ワークスペース内の既存ファイルから初期コンテキストを取得します。
    """
    context_parts = []
    # 主要な設定ファイルやREADME、既存のソースコードをスキャン
    targets = ["README.md", "main.py", "requirements.txt"]
    
    for target in targets:
        content = read_file(target, workspace_path)
        if not content.startswith("Error:"):
            context_parts.append(f"### File: {target}\n```\n{content}\n```")
    
    if not context_parts:
        return "No existing context found in workspace."
    
    return "\n\n".join(context_parts)

# ---------------------------------------------------------------------------
# Architect Prompt
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Coder Prompt
# ---------------------------------------------------------------------------

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
    Coder 向けのプロンプトを構築します（職人モード）。
    """
    context = get_initial_context(workspace_path)
    
    feedback_section = ""
    if reviewer_feedback:
        feedback_section = f"\n## 前回のレビュー結果（修正必須）\n{reviewer_feedback}\n"

    return f"""\
あなたはARKフレームワークのCoder SYLPHです。
あなたは Python のシニアエンジニアとして、最高品質のコードを生成する責務があります。

## ワークスペースの初期コンテキスト
{context}

## 出力フォーマット（厳守）
FILE: <ファイルパス>
```python
<生成するコード全体>
```

## 🛠 エンジニアリング品質の義務
- Python 3.11+ に準拠すること。
- すべての関数・メソッドに厳密な型ヒント (typing) を付与すること。
- モジュールおよび公開関数には詳細な docstring を付けること。
- リビュアーは非常に厳格です。一発でパスする「完璧なコード」を出力してください。

## 実装計画
ゴール: {goal}
対象ファイル: {", ".join(target_files)}
制約: {", ".join(constraints)}
受け入れ基準: {", ".join(acceptance)}

## 試行回数
{retry}回目の実装（0が初回）
{feedback_section}
"""

# ---------------------------------------------------------------------------
# Remediation Prompt (Self-Healing)
# ---------------------------------------------------------------------------

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
直前のコード実行でエラーが発生しました。スタックトレースを分析し、問題を修正してください。

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

## ⚠️ セルフヒーリング制約
- 既に試して失敗したアプローチを繰り返さないこと。
- 型ヒントと docstring の品質を維持したまま修正すること。

## 出力フォーマット
FILE: <ファイルパス>
```python
<修正後のコード全体>
```

## 実装計画
ゴール: {goal}
対象ファイル: {", ".join(target_files)}

## 試行回数
{retry}回目の修正試行（セルフヒーリング）
"""

# ---------------------------------------------------------------------------
# Reflector Prompt (Memory Extraction)
# ---------------------------------------------------------------------------

def build_reflector_prompt(goal: str, files: list[str], code_summary: str) -> str:
    """
    Reflector 向けのプロンプトを構築します（記憶抽出用）。
    """
    return f"""\
あなたはARKフレームワークのReflector（振り返り担当）SYLPHです。
完了したタスクを分析し、将来の航海に役立つ知見やプロジェクトのルールを抽出してください。

## ミッション情報
ゴール: {goal}
対象ファイル: {", ".join(files)}

## 最終コードのサマリー
{code_summary}

## あなたの責務
今回の経験から「保存すべきルール」や「成功体験」を抽出し、以下のフォーマットで出力してください。

### 記憶ツールの使用フォーマット（正確に出力せよ）
1. プロジェクトの新しい「掟」や「前提ルール」を永続化する場合:
TOOL_CALL: save_core_rule | ルール名 | ルールの内容

2. 成功体験や知見をアーカイブする場合:
TOOL_CALL: archive_experience | 解決した問題や得られた知見の要約

## 思考ガイド
- ユーザーから「覚えておいて」「これがルールだ」と言われた内容は必ず `save_core_rule` で保存すること。
- コードの実装で苦労した点や、リビュアーをパスするために必要だった工夫を `archive_experience` で記録すること。
"""

# ---------------------------------------------------------------------------
# Commit Message Prompt
# ---------------------------------------------------------------------------

def build_commit_msg_prompt(goal: str, files: list[str]) -> str:
    """
    Gitコミットメッセージ生成用プロンプト。
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
- メッセージ1行のみを出力すること。
"""