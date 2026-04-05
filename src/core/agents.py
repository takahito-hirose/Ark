"""
ARK — Agents Prompt Core (Clean Edition)
=====================================================
Phase 12: The Grand Fleet & TDD Pipeline
エージェントの「知能」と「規律」を司るプロンプト工場。
小型LLMでも誤動作しないよう、ノイズとなるロールプレイ要素や
複雑な差分フォーマットの強制を排除し、
複数ファイルであっても「完全なコード」を確実に出力させる厳格なプロンプトです。
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
Break down the goal into a sequence of actionable SUBTASKS.
{new_project_hint}
## Workspace State
{file_tree}

{blueprints_section}
{rules_section}{exp_section}
## Goal
{goal}

## Strict Rules
1. Break down the entire goal into logical, sequential tasks (Work Breakdown Structure).
2. Only output file names in TARGET_FILES (e.g., `main.py`, not `workspace/main.py`).
3. Prioritize modifying existing files over creating new ones if applicable.
4. If Past Experiences or Avoidance Rules exist, formulate constraints to explicitly avoid known failures.
5. Provide a test code snippet that verifies the core logic of the tasks for TDD (Test-Driven Development).

## Output Format (Strictly follow this structure)
TARGET_FILES: <file1>, <file2>
CONSTRAINTS: <constraint1>, <constraint2>
ACCEPTANCE: <acceptance criteria>
TASKS:
- ID: task-1 | TITLE: <task title> | DESC: <detailed description> | DEPENDS: <none or task_id>
- ID: task-2 | TITLE: <task title> | DESC: <detailed description> | DEPENDS: task-1

TEST_CODE:
```python
# Write initial test code snippet here (pytest/unittest format) to verify the logic.
# If no tests are required, write: # No tests required
```
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
    Coder 向けのプロンプト（完全コード・複数ファイル対応厳格版）。
    """
    unique_targets = list(dict.fromkeys(target_files))
    context = ""
    for target in unique_targets:
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
3. NO EXPLANATIONS: Provide ONLY the code blocks formatted exactly as shown below. Do NOT add ANY conversational text, introductions, or markdown explanations outside the code block.
4. MULTIPLE FILES: If you need to create or modify multiple files, repeat the EXACT `FILE: ...` and code block format for EACH file consecutively.

## Output Format (MANDATORY)
For EVERY file you need to create or modify, use this EXACT structure. Do not output anything else.

FILE: <filename>
```<language>
<Full complete code for the file>
```

FILE: <another_filename>
```<language>
<Full complete code for the file>
```

## Task Details
GOAL: {goal}
CONSTRAINTS: {constraints_text}

## Target Files Content
{context}

Attempt: {retry}
{feedback_section}
Output the complete, fully updated code now, adhering strictly to the Output Format.
"""

# ---------------------------------------------------------------------------
# Remediation Prompt
# ---------------------------------------------------------------------------

def build_remediation_prompt(goal, target_files, retry, workspace_path, failure_reason, stacktrace, current_source, attempt_history=None) -> str:
    """
    エラー発生時の自己修復用プロンプト（完全コード・複数ファイル対応厳格版）。
    """
    unique_targets = list(dict.fromkeys(target_files)) if target_files else ["unknown.py"]
    targets_str = ", ".join(unique_targets)

    current_code_section = f"## Current Source Code\n{current_source}\n" if current_source else ""

    return f"""\
You are the Coder Agent. The previous execution resulted in an error. Please fix the issue.

GOAL: {goal}
TARGET FILES: {targets_str}

[ERROR REASON]
{failure_reason}

[STACKTRACE]
{stacktrace}

{current_code_section}
## Instructions
Fix the error and output the ENTIRE corrected code for all affected files.
1. DO NOT use diff markers. Output the full file content.
2. DO NOT include any conversational text, explanations, or notes. Output ONLY the files and code blocks.
3. If multiple files need fixing, output each one consecutively using the exact format.

## Output Format (MANDATORY)
FILE: <filename>
```<language>
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
    """
    return f"""\
Goal: {goal}
Modified Files: {", ".join(files)}
Generate a single-line git commit message based on the above. Format: <type>: <description> (English)
"""

# ---------------------------------------------------------------------------
# Next Course Proposal Prompt
# ---------------------------------------------------------------------------

def build_next_course_prompt(
    original_goal: str,
    workspace_path: Path,
    completed_tasks_summary: str,
    core_rules: str = ""
) -> str:
    """
    フェーズ完了後、Architectに自律的に次のミッションを提案させるプロンプト。
    """
    file_tree = get_file_tree(workspace_path)
    rules_section = f"## 📜 Core Project Rules\n{core_rules}\n" if core_rules else ""
    
    # タスクサマリーが空の場合のフォールバック
    completed_tasks_summary = completed_tasks_summary or "No specific tasks recorded, but initial setup phase completed."

    return f"""\
You are the Architect Agent. The initial phase of the project has just completed successfully.
Your role is to analyze the current workspace and the original goal, and autonomously propose the NEXT actionable mission (Next Course).

## Original Ultimate Goal
{original_goal}

## What Was Just Completed
{completed_tasks_summary}

## Current Workspace State
{file_tree}

{rules_section}

## Strict Instructions
1. Analyze the gap between the "Current Workspace State" and the "Original Ultimate Goal".
2. Define a single, highly focused NEXT GOAL that logically moves the project forward.
3. Identify expected artifacts (files to be created or modified) and potential risks.
4. DO NOT wrap your output in markdown code blocks (e.g., ```yaml or ```). Output raw text.
5. Output MUST be strictly in the following key-value format.

## Output Format (MANDATORY)
NEXT_GOAL: <A clear, single-sentence description of the next mission>
EXPECTED_ARTIFACTS: <file1, file2>
RISKS: <Identify any potential technical risks or missing dependencies>
"""