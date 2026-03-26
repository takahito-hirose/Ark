"""
ARK — Agents Prompt Core (Clean Edition)
=====================================================
エージェントの「知能」と「規律」を司るプロンプト工場。
小型LLMでも誤動作しないよう、ノイズとなるロールプレイ要素や
複雑な差分フォーマット(SEARCH/REPLACE)の強制を排除し、
常に「完全なコード」を出力させる厳格なシステムプロンプトとして最適化しました💋

※各関数のDocstring（関数直下のコメント）に、
  生成される英語プロンプトの「日本語での意訳・狙い」を詳細に記載しています。
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

# ---------------------------------------------------------------------------
# Architect Prompt Builder
# ---------------------------------------------------------------------------

def build_architect_prompt(
    goal: str, 
    workspace_path: Path, 
    blueprints: str = "",
    core_rules: str = "",
    past_experiences: str = ""
) -> str:
    """
    Architect 向けのプロンプトを構築します。
    
    【日本語の意訳・指示の狙い】
    役割: 既存のワークスペースと「過去の記憶」に基づいて修正計画を立てるアーキテクト（設計者）。
    ルール:
    1. TARGET_FILES にはファイル名のみを出力すること（パス名を含めない）。
    2. 新規作成よりも既存ファイルの修正を優先すること。
    3. [重要] 過去の失敗(Anti-Patterns)がある場合は、絶対に同じ轍を踏まないよう計画(CONSTRAINTS)に反映させること。
    
    出力フォーマット:
    TARGET_FILES: <ファイル名1>, <ファイル名2>
    CONSTRAINTS: <制約事項1>, <制約事項2>
    ACCEPTANCE: <成功の定義>
    ※空プロジェクトの場合は「適切なファイル名を決めて」とヒントを出します。
    """
    file_tree = get_file_tree(workspace_path)
    
    new_project_hint = ""
    if "- " not in file_tree:
        new_project_hint = "\n[Notice] Workspace is currently empty. Determine appropriate file names for the new project.\n"

    blueprints_section = f"## Project Blueprints (AST Outlines)\n{blueprints}\n" if blueprints else ""
    rules_section = f"## 📜 Core Project Rules\n{core_rules}\n(You MUST adhere to these global rules.)\n" if core_rules else ""
    exp_section = f"## 🧠 Past Experiences & Avoidance Rules\n{past_experiences}\n(Pay VERY close attention to past failure patterns and DO NOT repeat them.)\n" if past_experiences else ""

    return f"""\
You are the Architect Agent. Your role is to plan the necessary modifications to achieve the user's goal based on the existing workspace.
{new_project_hint}
## Workspace State
{file_tree}

{blueprints_section}
{rules_section}{exp_section}
## Goal
{goal}

## Strict Rules
1. Only output file names in TARGET_FILES (e.g., `main.py`, not `workspace/main.py`).
2. Prioritize modifying existing files over creating new ones if applicable.
3. If Past Experiences or Avoidance Rules exist, formulate constraints to explicitly avoid known failures.

## Output Format (Strictly follow this structure)
TARGET_FILES: <file1>, <file2>
CONSTRAINTS: <constraint1>, <constraint2>
ACCEPTANCE: <acceptance criteria>
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
    search_results: str = "",
    core_rules: str = ""
) -> str:
    """
    Coder 向けのプロンプト（完全コード出力版）。
    
    【日本語の意訳・指示の狙い】
    役割: 指示通りに正確にコードを修正するコーダー。
    ★重要変更★ 差分(SEARCH/REPLACE)形式での出力をやめさせ、**常にファイルの完全なコード(Full Code)** を出力させます。
    ルール:
    1. 完全出力: コードの一部を省略したりせず、ファイル全体のコードを出力すること。
    2. マーカー禁止: Gitのコンフリクトマーカー（<<<<<<<など）や差分表現は絶対に使わないこと。
    3. 無駄話禁止: コードブロックだけを出力し、会話文や解説を一切書かないこと。
    特記事項: 
    - 検索結果(search_results)がある場合は、それを最優先の知識として実装に反映させる。
    - 全体ルール(core_rules)がある場合は、命名規則などに従う。
    - 以前失敗した場合は reviewer_feedback が渡され、同じミスを防ぐ。
    """
    context = ""
    for target in target_files:
        clean_target = Path(target).name
        content = read_file(clean_target, workspace_path)
        
        if not content.startswith("Error:"):
            context += f"### File: {clean_target} (Current Content)\n"
            context += f"```python\n{content}\n```\n\n"
        else:
            context += f"### File: {clean_target}\n(This is a new file to be created. It is currently EMPTY.)\n\n"

    constraints_text = "\n".join([f"- {c}" for c in constraints]) if constraints else "None"
    
    search_section = f"## Latest Research Data (Priority Knowledge)\n{search_results}\n" if search_results else ""
    rules_section = f"## 📜 Core Project Rules\n{core_rules}\n" if core_rules else ""
    feedback_section = f"## Reviewer Feedback from previous failure:\n{reviewer_feedback}\n" if reviewer_feedback else ""

    return f"""\
You are the Coder Agent. Your task is to implement the goal by outputting the FULL, completely updated code for the target files.
{rules_section}{search_section}
## Strict Rules for Code Generation
1. FULL FILE CONTENT: You MUST output the entire, complete code for the file. Do not truncate or omit any parts of the code.
2. NO DIFF MARKERS: NEVER use git conflict markers or diff blocks (e.g., `<<<<<<<`, `=======`, `>>>>>>>`).
3. NO EXPLANATIONS: Provide ONLY the code blocks. Do not add conversational text or markdown explanations outside the code block.

## Example Format
FILE: main.py
```python
import os

def main():
    print("Complete file code goes here")

if __name__ == "__main__":
    main()
```

## Task Details
GOAL: {goal}
CONSTRAINTS: {constraints_text}

## Target Files Content
{context}

Attempt: {retry}
{feedback_section}
Output the complete, fully updated code now.
"""

# ---------------------------------------------------------------------------
# Remediation Prompt
# ---------------------------------------------------------------------------

def build_remediation_prompt(goal, target_files, retry, workspace_path, failure_reason, stacktrace, current_source, attempt_history=None) -> str:
    """
    エラー発生時の自己修復用プロンプト（完全コード出力版）。
    
    【日本語の意訳・指示の狙い】
    役割: 実行時エラーを修正する緊急コーダー。
    指示内容: 前回の実行で発生したエラー理由とスタックトレースを読み込み、
             原因を修正した **正しい完全なコード** を出力し直すこと。
             会話文は一切不要。Diffマーカーも使用禁止。
    """
    target_file = Path(target_files[0]).name if target_files else "unknown.py"
    return f"""\
You are the Coder Agent. The previous execution resulted in an error. Please fix the issue.

GOAL: {goal}

[ERROR REASON]
{failure_reason}

[STACKTRACE]
{stacktrace}

## Instructions
Fix the error and output the ENTIRE corrected code.
DO NOT use diff markers (e.g., `<<<<<<<`, `>>>>>>>`). Output the full file content.
Do not include any conversational text.

## Output Format
FILE: {target_file}
```python
<Entire Corrected Code Here>
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
    search_results: str = ""
) -> str:
    """
    Reviewer 向けのプロンプトを構築。
    
    【日本語の意訳・指示の狙い】
    役割: 提出されたコードを評価し、PASS/FAILを判定するレビュアー。
    評価基準:
    1. ユーザーの目的(Goal)を達成しているか。
    2. 受け入れ基準(Acceptance Criteria)を満たしているか。
    3. ★重要変更★ コードの完全性(Code Integrity)。<<<<<<< などのGitコンフリクトマーカーや、
       シンタックスエラーを起こすようなゴミがコードに混入していないかを確認する。
    4. (検索結果がある場合) 最新のリサーチ情報が正しく反映されているか。
    出力フォーマット:
    VERDICT: PASS or FAIL
    SCORE: <0.0〜1.0>
    SUMMARY: <1行の要約>
    ISSUES: <深刻度>|<ファイル>|<行>|<メッセージ> （あれば）
    """
    search_hint = f"\n## Research Criteria\nEnsure the following information is reflected correctly:\n{search_results}" if search_results else ""

    return f"""\
You are the Reviewer Agent. Evaluate the provided code and determine if it meets the criteria.
{search_hint}

## Submitted Code
{code_summary}

## Evaluation Criteria
1. Goal Fulfillment: {goal}
2. Acceptance Criteria: {acceptance}
3. Code Integrity: Ensure the code is complete and absolutely free of any git conflict markers (e.g., `<<<<<<<`, `=======`, `>>>>>>>`) or syntax errors.

## Output Format (Strictly follow this structure)
VERDICT: PASS or FAIL
SCORE: <float between 0.0 and 1.0>
SUMMARY: <One line summary of the review>
ISSUES: <severity>|<file>|<line>|<message> (List any issues, or omit if none)
"""

# ---------------------------------------------------------------------------
# Reflector Prompt
# ---------------------------------------------------------------------------

def build_reflector_prompt(
    goal: str, 
    files: list[str], 
    code_summary: str, 
    search_results: str = "",
    attempt_history_str: str = "",
    is_failure: bool = False
) -> str:
    """
    Reflector 向けのプロンプト（記憶抽出用）。
    
    【日本語の意訳・指示の狙い】
    役割: 今回のミッションから得られた知見を大図書館(ChromaDB)に保存する司書。
    抽出対象:
    - 実装の工夫、エラーの解決策、アーキテクチャの決定事項。
    - プロジェクト特有のルール。
    - 検索で得られた新仕様。
    - 試行錯誤の履歴(attempt_history)から「失敗パターン」と「成功コード」。
    - 🚨 (is_failure=True時) 致命的な失敗の原因を徹底分析し、二度と同じミスを繰り返さないための「地雷マップ(Avoidance Rules)」を作成する！
    ルール:
    必ず指定の TOOL_CALL 形式（1行に1つ）で出力すること。
    [フォーマット1: 全体ルール保存] TOOL_CALL: save_core_rule | <ルール名> | <詳細>
    [フォーマット2: 経験の保存] TOOL_CALL: archive_experience | [Failure Pattern] <エラー原因> -> [Success Snippet/Avoidance] <解決策・回避策>
    """
    search_hint = f"\n## New Insights (Research Data)\n{search_results}\nArchive any new specifications or differences found." if search_results else ""
    history_hint = f"\n## Trial & Error History\n{attempt_history_str}\nAnalyze this history to extract 'Failure Patterns' and their 'Success Snippets'." if attempt_history_str else ""
    
    failure_directive = ""
    if is_failure:
        failure_directive = """
## 🚨 CRITICAL FAILURE ANALYSIS MODE 🚨
The mission ultimately FAILED after maximum retries. 
Your primary objective is NO LONGER to extract success stories, but to deeply analyze WHY the process failed and to map out the "Anti-Patterns" (Landmines).
- What logic was fundamentally flawed?
- What repeating errors occurred during the attempt history?
- Extract these fatal mistakes and formulate clear "Avoidance Rules" (Negative Knowledge) to prevent future agents from making the same errors.
"""

    return f"""\
You are the Reflector Agent. Your task is to archive the experience and knowledge gained from this mission.
{failure_directive}
## Extraction Targets{search_hint}{history_hint}
- Code implementations, solutions to errors, and architectural decisions.
- Project-specific rules or user preferences.
- If in Failure Mode, focus heavily on extracting Anti-Patterns and Avoidance Rules.

## Tool Usage Instructions (Strict)
Use the following format to call tools. One tool call per line.

1. Save a core project rule (or Avoidance Rule):
TOOL_CALL: save_core_rule | <rule_name_snake_case> | <rule_description>

2. Archive an experience/solution/anti-pattern:
TOOL_CALL: archive_experience | [Failure Pattern] <What failed/Error> -> [Success Snippet/Avoidance] <How it was solved/How to avoid it>

[Example Archive]
TOOL_CALL: archive_experience | [Failure Pattern] FastAPI OPTIONS request causes CORS error -> [Success Snippet] Configure CORSMiddleware allow_methods to include "*" for preflight requests.
TOOL_CALL: archive_experience | [Failure Pattern] Agent repeatedly tried to use non-existent DOM element -> [Avoidance] Always add a DOM wait/check logic before manipulating elements in JS.

Goal: {goal}
Modified Files: {", ".join(files)}
"""

# ---------------------------------------------------------------------------
# Garbage Collection (GC) Prompt
# ---------------------------------------------------------------------------

def build_gc_prompt(current_memory_dump: str) -> str:
    """
    Reflector 向けの記憶整理（ガベージコレクション）用プロンプト。
    
    【日本語の意訳・指示の狙い】
    役割: 定期的に記憶データベースの重複・矛盾を整理する司書。
    ルール:
    1. 似たようなルールや経験を統合(Deduplication)する。
    2. 古い情報と新しい情報で矛盾があれば、最新または汎用的な方を残す。
    3. 無意味なプレースホルダーデータ（例："rule_name"）は削除する。
    4. Markdownの装飾(```json)を含めず、純粋でパース可能なJSON文字列のみを出力すること。
    """
    return f"""\
You are the Reflector Agent managing the knowledge base.
Analyze the provided "Current Memory Dump" and reconstruct it following these rules:

## Reorganization Rules
1. Deduplication: Merge similar rules or experiences.
2. Conflict Resolution: If old and new information conflict, keep the most recent or generic one.
3. Clean Up: Remove meaningless placeholder data (e.g., "rule_name", "experience_summary").
4. Output Format: Output ONLY a valid JSON string. Do not include markdown code blocks like ```json.

## Example Output Format
{{
  "core_rules": {{
    "tech_stack": "Use Next.js and Python",
    "naming_convention": "Variables must be snake_case"
  }},
  "experiences": [
    {{
      "summary": "To fix FastAPI CORS errors, add CORSMiddleware.",
      "source": "local_execution",
      "trust_level": "verified"
    }}
  ]
}}

## Current Memory Dump
{current_memory_dump}
"""

# ---------------------------------------------------------------------------
# Commit Message Prompt
# ---------------------------------------------------------------------------

def build_commit_msg_prompt(goal: str, files: list[str]) -> str:
    """
    Gitコミットメッセージ生成用プロンプト。
    
    【日本語の意訳・指示の狙い】
    指定されたゴールと変更ファイル一覧から、
    <type>: <description> 形式の英語のコミットメッセージを1行で生成させる。
    """
    return f"""\
Goal: {goal}
Modified Files: {", ".join(files)}
Generate a single-line git commit message based on the above. Format: <type>: <description> (English)
"""