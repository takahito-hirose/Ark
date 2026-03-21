"""
ARK — Agents Prompt Core (Surgical Shield Edition)
=====================================================
エージェントの「知能」と「規律」を司るプロンプト工場。
既存コードを破壊させないための「防護壁」と、
Telescope（検索結果）を全ての精霊に同期する「神経系」を統合したわよ！💋
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from src.core.tools import read_file

log = logging.getLogger("ARK.AgentsCore")

# ---------------------------------------------------------------------------
# Shared Context Helpers
# ---------------------------------------------------------------------------

def get_initial_context(workspace_path: Path, targets: list[str] | None = None) -> str:
    """
    ワークスペース内の既存ファイルから初期コンテキストを取得します。
    """
    if targets is None:
        # デフォルトで探す一般的なファイル
        targets = ["README.md", "main.py", "requirements.txt"]
        
    context_parts = []
    
    for target in targets:
        # 常にファイル名のみを対象にする
        clean_target = Path(target).name
        content = read_file(clean_target, workspace_path)
        # エラーメッセージ("Error: ...")でなければコンテキストに追加
        if not content.startswith("Error:"):
            context_parts.append(f"### File: {clean_target}\n```python\n{content}\n```")
    
    if not context_parts:
        return "No existing context found in workspace."
    
    return "\n\n".join(context_parts)

def get_file_tree(workspace_path: Path) -> str:
    """
    ワークスペース内のファイル構造をスキャンして、LLMが理解しやすいツリー形式で返します。
    隔離機能を強化し、他のプロジェクトフォルダを無視します。
    """
    lines = []
    # 無視するディレクトリ（他プロジェクトのフォルダも含む）
    ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".ark_memory"}
    
    if not workspace_path or not workspace_path.exists():
        return "No files found (Empty Workspace)."

    try:
        for root, dirs, files in os.walk(workspace_path):
            # 🌟 [Strict Isolation] 
            # 1. 無視リストにあるもの 2. 他のプロジェクトフォルダ(ark-project-*) を除外
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith("ark-project-")]
            
            rel_path = os.path.relpath(root, workspace_path)
            depth = 0 if rel_path == "." else rel_path.count(os.sep) + 1
            indent = "  " * depth
            
            folder_name = os.path.basename(root) if rel_path != "." else "root"
            lines.append(f"{indent}📁 {folder_name}/")
            
            sub_indent = "  " * (depth + 1)
            for f in files:
                if not f.startswith("."):
                    lines.append(f"{sub_indent}📄 {f}")
    except Exception as e:
        return f"Error scanning workspace: {e}"
        
    return "\n".join(lines) if lines else "No files found."

# ---------------------------------------------------------------------------
# Architect Prompt Builder
# ---------------------------------------------------------------------------

def build_architect_prompt(goal: str, workspace_path: Path, blueprints: str = "") -> str:
    """
    Architect 向けのプロンプトを構築します。
    """
    file_tree = get_file_tree(workspace_path)
    
    # 新規プロジェクト時のヒントを追加
    new_project_hint = ""
    if "📄" not in file_tree:
        new_project_hint = "\n【🚨 新規ミッション】現在は空のプロジェクトです。適切なファイル名を決めて新規作成してください。\n"

    blueprints_section = ""
    if blueprints:
        blueprints_section = f"## 🏗️ プロジェクト設計図 (AST Outlines)\n以下は主要なPythonファイルの構造（クラスと関数）です。コードの全体像の把握に活用してください。\n{blueprints}\n"

    return f"""\
あなたはARKのArchitect SYLPH。プロジェクトの全資産を把握する最高司令官です。
既存のコードベースを尊重し、ゴールを達成するための「最小かつ正確な」改修計画を立ててください。
{new_project_hint}
## 📂 現在のドック（ワークスペース）の状況
{file_tree}

{blueprints_section}
## 🎯 ミッション
GOAL: {goal}

## 🛡️ 計画立案の鉄則（絶対遵守）
1. ファイル名のみを出力せよ: 
   - TARGET_FILES には `hello.py` のように「ファイル名だけ」を書いてください。
   - `workspace/` などのフォルダ名を含めるとエラーになるので絶対に禁止です。

2. 既存ファイル優先の原則: 
   - 上記ツリーに `📄` ファイルがある場合は、それを改修対象として優先してください。

## 📝 出力形式（これ以外は喋るな）
TARGET_FILES: <ファイル名1>, <ファイル名2>
CONSTRAINTS: <制約事項>
ACCEPTANCE: <成功の定義>
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
    reviewer_feedback: str = "",
    search_results: str = "" # 🌟 追加: 検索結果を受け取る！
) -> str:
    """
    Coder 向けのプロンプトを構築します。
    """
    context = ""
    for target in target_files:
        # パスが含まれていても Path(target).name でファイル名だけにする
        clean_target = Path(target).name
        content = read_file(clean_target, workspace_path)
        
        if not content.startswith("Error:"):
            # 🌟 [注意] パッチエンジンが行番号を嫌うので、行番号付与はやめる！そのままのソースを渡す💋
            context += f"### File: {clean_target} (Current Content)\n"
            context += f"```python\n{content}\n```\n\n"
        else:
            context += f"### File: {clean_target}\n(This is a new file to be created. It is currently EMPTY.)\n\n"

    constraints_text = "\n".join([f"- {c}" for c in constraints]) if constraints else "特になし"
    
    # 🌟 検索結果セクションの構築
    search_section = ""
    if search_results:
        search_section = f"""
## 🔭 最新リサーチ結果 (Telescope Insights)
外界の検索により、以下の最新情報が見つかりました。
あなたの事前学習データよりも、この情報を**「絶対の正解」**として最優先で採用してください。
---
{search_results}
---
"""

    return f"""\
あなたはARKのCoder SYLPH、世界最高峰の精密外科医です。
必ず「SEARCH/REPLACE」パッチを用いて、患者（既存コード）を完璧に治療します。
{search_section}
## 🏥 外科手術・成功の鍵（SEARCHブロックの掟）
1. 完全一致の義務: `<<<<<<< SEARCH` ブロックには、提供されたソースコードから、修正したい部分を「1文字の狂いもなく」完全にコピーしてください。
2. 新規ファイルの場合: `SEARCH` ブロックの中身を「空（何も書かない）」にしてください。
3. 最新情報の遵守: Telescope Insights がある場合、その内容を必ずコードに反映してください。
4. 挨拶はギャル語💋: ユーザーの要求に従い、アゲみざわなコードを書いてください（コメントの末尾には 💋 をつけること）。

## 💡 完璧な出力例（既存ファイルの修正）
FILE: hello.py
```python
<<<<<<< SEARCH
def greet():
    print("Hello")
=======
def greet():
    print("やっほー！ARKでパッチ当てちゃった💋")
>>>>>>> REPLACE
```

## 🎯 今回のオペ内容
ゴール: {goal}
制約: {constraints_text}

## 🔍 執刀対象の生データ（ここからSEARCH対象を精密に抽出せよ）
{context}

試行回数: {retry}
{f"## 前回の失敗フィードバック: {reviewer_feedback}" if reviewer_feedback else ""}

さあ、余計な前置きや解説は一切不要です。パッチだけを出力してください！🚀💋
"""

# ---------------------------------------------------------------------------
# Remediation Prompt
# ---------------------------------------------------------------------------

def build_remediation_prompt(goal, target_files, retry, workspace_path, failure_reason, stacktrace, current_source, attempt_history=None) -> str:
    """
    エラー発生時の自己修復用プロンプト。
    """
    target_file = Path(target_files[0]).name if target_files else "unknown.py"
    return f"""\
あなたはARKのCoder SYLPH。前回のパッチがエラーを引き起こしました。緊急オペを開始します。💋

GOAL: {goal}

【🚨 発生したエラー】
{failure_reason}

【🔥 スタックトレース】
{stacktrace}

## 救急処置の指示
エラーを修正した正しいコードを「SEARCH/REPLACE」形式で再生成してください。
マークダウンのコードブロック(` ```python `)を使って出力してください。

## 出力フォーマット
FILE: {target_file}
```python
<<<<<<< SEARCH
<現在の不具合のあるコード>
=======
<修正した正しいコード>
>>>>>>> REPLACE
```
"""

# ---------------------------------------------------------------------------
# Reviewer Prompt
# ---------------------------------------------------------------------------

def build_reviewer_prompt(
    goal: str,
    code_summary: str,
    acceptance: str,
    retry: int,
    search_results: str = "" # 🌟 追加: レビュアーにも検索結果を渡す！
) -> str:
    """
    Reviewer 向けのプロンプトを構築。
    """
    search_hint = f"\n## 🔭 最新リサーチの基準\n以下の情報がコードに正しく反映されているか厳密にチェックしてください:\n{search_results}" if search_results else ""

    return f"""\
あなたはARKフレームワークのReviewer SYLPHです。
提出されたコードを審査し、実務的な観点からPASS/FAILを判定してください。
{search_hint}

## 提出されたコード内容
{code_summary}

## 審査の優先順位
1. **最新仕様の反映**: Telescope Insights（リサーチ結果）がある場合、それが反映されているか（なければFAIL）。
2. **ユーザーのゴール達成**: {goal}
3. **受け入れ基準の遵守**: {acceptance}
4. **パッチ形式の正確性**: SEARCH/REPLACEブロックが正しく機能しているか。

## 出力フォーマット（厳守）
VERDICT: PASS または FAIL
SCORE: 0.0〜1.0の数値
SUMMARY: 審査結果の要約（1行）
ISSUES: <severity>|<file>|<line>|<message> の形式で列挙（なければ省略）
"""

# ---------------------------------------------------------------------------
# Reflector Prompt
# ---------------------------------------------------------------------------

def build_reflector_prompt(goal: str, files: list[str], code_summary: str, search_results: str = "") -> str:
    """
    Reflector 向けのプロンプト（記憶抽出用）。
    """
    search_hint = f"\n## 今回得られた新知見 (Telescope Insights)\n{search_results}\n※この最新仕様とこれまでの書き方の違いなどを優先的にアーカイブすること。" if search_results else ""

    return f"""\
あなたはARKのReflector SYLPHです。今回の経験をアーカイブしてください。

## 記憶すべきポイント{search_hint}
- 今回実装したコードの工夫や、エラーを解決した知見。
- ユーザーからの強い要望やプロジェクト独自のルール。

## 記憶ツールの使用
TOOL_CALL: save_core_rule | ルール名 | 内容
TOOL_CALL: archive_experience | 知見の要約

ゴール: {goal}
変更ファイル: {", ".join(files)}
"""

# ---------------------------------------------------------------------------
# Commit Message Prompt
# ---------------------------------------------------------------------------

def build_commit_msg_prompt(goal: str, files: list[str]) -> str:
    """
    Gitコミットメッセージ生成用。
    """
    return f"""\
ゴール: {goal}
変更ファイル: {", ".join(files)}
上記に基づき、1行のGitコミットメッセージを生成せよ。形式: <type>: <description> (English)
"""