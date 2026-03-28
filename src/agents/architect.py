"""
ARK — Architect Agent (SYLPH)
==============================
Phase 11: The Eternal Helmsman Update
設計フェーズを担当するエージェント。
外界の知識を覗き込む「望遠鏡（Telescope）」を装備し、
得られた知見をパーティ全員に共有する「神経系の中枢」よ💋

責務
----
- ユーザーのゴールを分析し、 PlanPayload と SubTaskリスト（WBS） を生成する。
- 既存プロジェクトのコンテキスト収集に加え、未知の技術に対する自律的な Web リサーチを行う。
- 獲得した最新の知見（search_results）を Payload に格納し、全エージェントに同期する。💋
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from src.agents.base_agent import BaseAgent
from src.core.agents import build_architect_prompt, get_file_tree
# 🌟 NEW: SubTask をインポートに追加！
from src.core.models import PlanPayload, SubTask, TaskStatus
from src.tools.ast_analyzer import generate_code_outline
from src.tools.telescope import WebTelescope

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Architect")

# ---------------------------------------------------------------------------
# ArchitectAgent
# ---------------------------------------------------------------------------

class ArchitectAgent(BaseAgent):
    """設計担当SYLPHエージェント。"""

    def __init__(
        self, 
        provider: "BaseProvider", 
        workspace_path: Path | None = None,
        on_token_usage: Optional[Callable[[int], None]] = None,
        use_mock_telescope: bool = False
    ) -> None:
        super().__init__(
            provider, 
            role="architect", 
            workspace_path=workspace_path,
            on_token_usage=on_token_usage
        )
        self.telescope = WebTelescope(mock_mode=use_mock_telescope)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, goal: str, task_id: str) -> PlanPayload:
        """ゴールを分析し PlanPayload と SubTaskリスト を生成する。"""
        log.info("[Architect] Gathering context and analysing goal: %r", goal[:60])
        
        # 1. ワークスペースの構造（ファイルツリー）を取得
        tree = get_file_tree(self._workspace_path)
        blueprints = self._scan_blueprints()

        gathered_context = ""
        # 2. 既存プロジェクトの探索 (Context Gathering)
        if tree.count("📄") >= 1:
            log.info("🔍 [Architect] 既存プロジェクトを検知。内部コンテキスト探索を開始します...")
            gathered_context += self._investigate_project(goal, tree)
        
        # 3. 望遠鏡による外界リサーチ (Telescope Calibration)
        log.info("🔭 [Architect] 未知の技術が必要か判断し、必要なら外界をリサーチします...")
        external_knowledge = self._research_external_knowledge(goal)
        
        # 4. ゴールにコンテキストを注入
        enhanced_goal = goal
        if gathered_context:
            enhanced_goal += f"\n\n{gathered_context}\n"
        if external_knowledge:
            enhanced_goal += f"\n\n【🔭 望遠鏡で獲得した最新の知識】\n{external_knowledge}\n"

        # 5. 設計図をプロンプトに渡してLLMを呼び出す
        prompt = build_architect_prompt(enhanced_goal, self._workspace_path, blueprints=blueprints)
        response = self._call_llm(prompt)
        
        # 6. レスポンスをパースしてPayloadを作成
        return self._parse_response(
            response, 
            goal=goal, 
            task_id=task_id, 
            search_results=external_knowledge
        )

    # ------------------------------------------------------------------
    # Context & External Research Methods
    # ------------------------------------------------------------------

    def _research_external_knowledge(self, goal: str) -> str:
        research_prompt = (
            "あなたはARKのArchitectです。\n"
            "以下のゴールを達成するために、あなたが知らない最新のライブラリや技術スタックの使い方が必要ですか？\n\n"
            f"【ゴール】\n{goal}\n\n"
            "【指示】\n"
            "もしWeb検索が必要であれば、検索クエリ（英語推奨）を一つだけ出力してください。\n"
            "出力フォーマット: SEARCH_QUERY: <検索キーワード>\n"
            "検索が不要な場合（既存知識で十分な場合）は SEARCH_QUERY: NONE と出力してください。"
        )
        
        response = self._call_llm(research_prompt)
        
        pattern = r"SEARCH_QUERY\s*:\s*(.+)"
        match = re.search(pattern, response, re.IGNORECASE)
        
        if match:
            query = match.group(1).strip()
            if query.upper() != "NONE":
                log.info(f"🔭 [Architect] 望遠鏡を起動します。検索クエリ: {query}")
                return self.telescope.research(query)
                
        return ""

    def _scan_blueprints(self) -> str:
        if not self._workspace_path or not self._workspace_path.exists():
            return ""
            
        py_files = list(self._workspace_path.glob("*.py"))
        if not py_files:
            return ""

        outlines = []
        ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".ark_memory"}
        
        for py_file in self._workspace_path.rglob("*.py"):
            if any(part in ignore_dirs for part in py_file.parts):
                continue
            if py_file.name.startswith("test_"):
                continue
                
            outline = generate_code_outline(py_file)
            if outline and not outline.startswith("# Error"):
                outlines.append(outline)
                
        if outlines:
            log.info("🧠 [Architect] Extracted AST blueprints from %d Python files.", len(outlines))
            
        return "\n\n".join(outlines)

    def _investigate_project(self, goal: str, tree: str) -> str:
        investigation_prompt = (
            "あなたはARKのArchitectです。\n"
            "既存のプロジェクトを改修するために、事前にどのファイルの中身を確認すべきか判断してください。\n\n"
            f"【ゴール】\n{goal}\n\n"
            f"【プロジェクト構造】\n```\n{tree}\n```\n\n"
            "【指示】\n"
            "確認が必要なファイルをカンマ区切りで出力してください。\n"
            "出力フォーマット: READ_FILES: path/to/file1.py, path/to/file2.py\n"
            "確認が不要な場合は READ_FILES: NONE と出力してください。"
        )
        
        response = self._call_llm(investigation_prompt)
        
        pattern = r"READ_FILES\s*:\s*(.+)"
        match = re.search(pattern, response, re.IGNORECASE)
        context_parts = []
        
        if match:
            files_str = match.group(1).strip()
            if files_str.upper() != "NONE":
                clean_files = [f.strip().replace("📄", "").replace("📁", "").strip() for f in files_str.split(",")]
                
                for fp in clean_files:
                    if not fp: continue
                    target_file = self._workspace_path / fp
                    if target_file.is_file():
                        try:
                            content = target_file.read_text(encoding="utf-8")
                            if len(content) > 10000:
                                content = content[:10000] + "\n... (truncated)"
                            context_parts.append(f"### File: {fp}\n```python\n{content}\n```")
                            log.info("📖 [Architect] Context read from: %s", fp)
                        except Exception as e:
                            log.warning("⚠️ Could not read %s: %s", fp, e)
                            
        return "\n\n".join(context_parts)

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    def _parse_response(
        self, 
        response: str, 
        *, 
        goal: str, 
        task_id: str, 
        search_results: str = ""
    ) -> PlanPayload:
        """LLMレスポンスから PlanPayload を抽出する。"""
        
        target_files   = self._extract_list(response, "TARGET_FILES")
        constraints    = self._extract_list(response, "CONSTRAINTS",   ["Python 3.11+", "型ヒント必須"])
        acceptance     = self._extract_list(response, "ACCEPTANCE",    ["no syntax errors", "file exists"])

        target_files = [Path(f).name for f in target_files if f]

        if not target_files:
            log.warning("⚠️ [Architect] TARGET_FILES のパースに失敗。レスポンスから推測します。")
            py_matches = re.findall(r'([\w\-\.]+\.py)', response)
            if py_matches:
                target_files = [Path(m).name for m in py_matches]
            else:
                target_files = [f"output_{task_id[:8]}.py"]

        # 🌟 NEW: サブタスク（海図）をパースして取り出す！
        tasks = self._parse_tasks(response)
        
        if tasks:
            log.info("🗺️ [Architect] Generated %d sub-tasks for the plan.", len(tasks))
        else:
            log.warning("⚠️ [Architect] No valid tasks found. Orchestrator might fall back to single-pass mode.")

        payload = PlanPayload(
            goal=goal,
            spec_path="specs/core_logic.md",
            target_files=target_files,
            constraints=constraints,
            acceptance_criteria=acceptance,
            search_results=search_results,
            tasks=tasks  # 🌟 ここにタスクリストをセット！
        )
        return payload

    def _parse_tasks(self, response: str) -> list[SubTask]:
        """レスポンス内の TASKS: セクションから SubTask のリストを抽出する"""
        tasks = []
        # TASKS: という文字以降をごっそり取得
        tasks_match = re.search(r'TASKS:\s*(.*?)(?:\n\n|\Z)', response, re.DOTALL | re.IGNORECASE)
        if not tasks_match:
            return tasks
            
        lines = tasks_match.group(1).strip().split('\n')
        for line in lines:
            if not line.strip().startswith('-'):
                continue
                
            # 例: - ID: task-1 | TITLE: Setup | DESC: ... | DEPENDS: task-0
            parts = [p.strip() for p in line.strip('- ').split('|')]
            task_dict = {}
            for part in parts:
                if ':' in part:
                    k, v = part.split(':', 1)
                    task_dict[k.strip().upper()] = v.strip()
                    
            if 'ID' in task_dict and 'TITLE' in task_dict and 'DESC' in task_dict:
                deps = []
                # 依存関係が書かれている場合だけパースする
                if 'DEPENDS' in task_dict and task_dict['DEPENDS'].lower() not in ['', 'none']:
                    deps = [d.strip() for d in task_dict['DEPENDS'].split(',')]
                    
                tasks.append(SubTask(
                    id=task_dict['ID'],
                    title=task_dict['TITLE'],
                    description=task_dict['DESC'],
                    dependencies=deps
                ))
                
        return tasks

    @staticmethod
    def _extract_list(text: str, key: str, default: list[str] | None = None) -> list[str]:
        if default is None:
            default = []
            
        pattern = rf"^{re.escape(key)}\s*:\s*(.+)$"
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if not match:
            return default
            
        raw = match.group(1).strip()
        raw = raw.replace("`", "").strip()
        
        items = [item.strip() for item in raw.split(",") if item.strip()]
        return items if items else default