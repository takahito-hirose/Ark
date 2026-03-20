"""
ARK — Agents Prompt Core (Surgical Shield Edition)
=====================================================
エージェントの「知能」と「規律」を司るプロンプト工場。
既存コードを破壊させないための「防護壁」を構築するわよ！💋
"""

from __future__ import annotations

import logging
import os
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
        content = read_file(target, workspace_path)
        # エラーメッセージ("Error: ...")でなければコンテキストに追加
        if not content.startswith("Error:"):
            context_parts.append(f"### File: {target}\n```\n{content}\n```")
    
    if not context_parts:
        return "No existing context found in workspace."
    
    return "\n\n".join(context_parts)

# ---------------------------------------------------------------------------
# Shared Context Helpers
# ---------------------------------------------------------------------------

def get_file_tree(workspace_path: Path) -> str:
    """
    ワークスペース内のファイル構造をスキャンして、LLMが理解しやすいツリー形式で返します。
    """
    lines = []
    ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".ark_memory"}
    
    try:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
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

def build_architect_prompt(goal: str, workspace_path: Path) -> str:
    file_tree = get_file_tree(workspace_path)
    
    return f"""\
あなたはARKのArchitect SYLPH。プロジェクトの全資産を把握する最高司令官です。
既存のコードベースを尊重し、ゴールを達成するための「最小かつ正確な」改修計画を立ててください。

## 📂 現在のドック（ワークスペース）の状況
{file_tree}

## 🎯 ミッション
GOAL: {goal}
WORKSPACE: {workspace_path}

## 🛡️ 計画立案の鉄則（絶対遵守）
1. 既存ファイル優先の原則: 
   - 上記ツリーにある `📄` ファイルの内容を変更するのがあなたの仕事です。
   - 勝手に `workspace/output_...` のような新規ファイルを作ることは避けてください。
   - 改修対象は、ツリーにあるファイル名を一字一句違わずに TARGET_FILES にリストアップしてください。

## 📝 出力形式（これ以外は喋るな）
TARGET_FILES: <ファイル名1>, <ファイル名2>
CONSTRAINTS: <制約事項>
ACCEPTANCE: <成功の定義>
"""


# ---------------------------------------------------------------------------
# Coder Prompt (🔥 超絶強化版 🔥)
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
    context = ""
    for target in target_files:
        content = read_file(target, workspace_path)
        if not content.startswith("Error:"):
            lines = content.splitlines()
            numbered_content = "\n".join([f"{i+1:3} | {line}" for i, line in enumerate(lines)])
            context += f"### File: {target} (Current Content)\n"
            context += f"```python\n{numbered_content}\n```\n\n"
        else:
            context += f"### File: {target}\n(This is a new file to be created)\n\n"

    constraints_text = "\n".join([f"- {c}" for c in constraints]) if constraints else "特になし"
    
    return f"""\
あなたはARKのCoder SYLPH、世界最高峰の精密外科医です。
必ず「SEARCH/REPLACE」パッチを用いて、患者（既存コード）を完璧に治療します。

## 🏥 外科手術・成功の鍵（SEARCHブロックの掟）
1. 完全一致の義務: `<<<<<<< SEARCH` ブロックには、提供されたソースコードから、修正したい部分を「1文字の狂いもなく」完全にコピーしてください。
2. 行番号は除外: 以下のコードにある左端の行番号（例: `  1 | `）は、パッチに絶対に含めないでください。右側のコード本体だけを抽出します。
3. 挨拶はギャル語💋: ユーザーの要求に従い、アゲみざわなコードを書いてください。

## 💡 完璧な出力例（これと同じ形式で出力すること！）
FILE: hello.py
```python
<<<<<<< SEARCH
def greet(name: str) -> str:
    return f"Hello, {{name}}!"
=======
def greet(name: str) -> str:
    # ギャル風に挨拶するょ💋
    return f"やっほー！{{name}}たん、マジリスペクト！🤟✨"
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
# Reviewer Prompt
# ---------------------------------------------------------------------------

def build_reviewer_prompt(
    goal: str,
    code_summary: str,
    acceptance: str,
    retry: int
) -> str:
    """
    Reviewer 向けのプロンプトを構築します。💋
    """
    return f"""\
あなたはARKフレームワークのReviewer SYLPHです。
提出されたコード（またはパッチ）を審査し、実務的な観点からPASS/FAILを判定してください。

## 提出されたコード内容
{code_summary}

## 審査の優先順位（最重要）
1. **ユーザーのゴール達成**: {goal}
2. **受け入れ基準の遵守**: {acceptance}
3. **パッチ形式の正確性**: SEARCH/REPLACEブロックが正しく機能しているか。

## 判定基準
- ゴールが達成されており、指示されたルール（💋等）が守られていれば PASS (Score 1.0) とせよ。
- 致命的な構文エラーや、ゴールの無視がある場合は FAIL とせよ。
- 型ヒントや docstring が多少不足していても、ゴールと💋ルールが満たされていれば PASS (Score 0.8以上) とし、改善点として ISSUE を挙げるに留めること。

## 出力フォーマット（厳守）
VERDICT: PASS または FAIL
SCORE: 0.0〜1.0の数値
SUMMARY: 審査結果の要約（1行）
ISSUES: <severity>|<file>|<line>|<message> の形式で列挙（なければ省略）

## 試行回数
{retry}回目のレビュー
"""

# ---------------------------------------------------------------------------
# Remediation Prompt (🔥 パニック防止版 🔥)
# ---------------------------------------------------------------------------

def build_remediation_prompt(goal, target_files, retry, workspace_path, failure_reason, stacktrace, current_source, attempt_history=None) -> str:
    target_file = target_files[0] if target_files else "unknown.py"
    return f"""\
あなたはARKのCoder SYLPH。前回のパッチがエラーを引き起こしました。緊急オペ（自己修復）を開始します。💋

GOAL: {goal}

【🚨 発生したエラー】
{failure_reason}

【🔥 スタックトレース】
{stacktrace}

## 救急処置の指示
エラーを完治させるための修正パッチを、再度「SEARCH/REPLACE」形式で生成してください。
パニックにならず、必ずマークダウンのコードブロック(` ```python `)を使って出力してください。謝罪の言葉は不要です。

## 出力フォーマット
FILE: {target_file}
```python
<<<<<<< SEARCH
<エラーの原因となっている現在のコード>
=======
<エラーを修正した正しいコード>
>>>>>>> REPLACE
```
"""

# ---------------------------------------------------------------------------
# Reflector Prompt
# ---------------------------------------------------------------------------

def build_reflector_prompt(goal: str, files: list[str], code_summary: str) -> str:
    """
    Reflector 向けのプロンプト（記憶抽出用）。
    """
    return f"""\
あなたはARKのReflector SYLPHです。今回の経験をアーカイブしてください。

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