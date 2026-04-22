"""
ARK — Architect Agent (SYLPH)
==============================
Phase 15: Domain-Driven Edition
設計フェーズを担当するエージェント。
外界の知識を覗き込む「望遠鏡（Telescope）」を装備し、
得られた知見をパーティ全員に共有する「神経系の中枢」よ💋
※プロンプトのコアは Skills.md に移譲されました！
"""

from __future__ import annotations

import logging
import re
import json
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from src.agents.base_agent import BaseAgent
# 🌟 旧プロンプトビルダーは削除！ get_file_tree だけ残す！
from src.core.agents import get_file_tree
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

        # 🌟 5. Phase 15: 動的コンテキストの構築 (Skills.mdはBaseAgentが結合してくれる)
        new_project_hint = ""
        if "- " not in tree:
            new_project_hint = "\n[Notice] Workspace is currently empty. Determine appropriate file names for the new project.\n"

        dynamic_context = f"""
        {new_project_hint}
        ## Workspace State
        {tree}

        ## Project Blueprints (AST Outlines)
        {blueprints}

        ## Goal
        {enhanced_goal}
        """

        response = self._call_llm(dynamic_context)
        
        # 6. レスポンスをパースしてPayloadを作成
        return self._parse_response(
            response, 
            goal=goal, 
            task_id=task_id, 
            search_results=external_knowledge
        )

    def propose_next_course(self, goal: str, workspace_state: str) -> dict:
        """現在の状態から次の開発フェーズを提案する"""
        
        prompt = (
            "【⚠️ IMPORTANT OVERRIDE】\n"
            "This is a special sub-task. IGNORE your standard output format (TARGET_FILES, TASKS, etc.).\n"
            "出力は必ず以下のキーを持つJSON形式のみとしてください:\n"
            "- next_goal: 次の目標（文字列）\n"
            "- expected_artifacts: 変更・作成が予想されるファイルのリスト（文字列の配列）\n"
            "- risks: 懸念事項やリスク（文字列）\n\n"
            f"【最終目標】\n{goal}\n\n"
            f"【現在のワークスペース状態】\n{workspace_state}\n\n"
            "さあ、次の航路を提案してください。"
        )
        
        log.info("🔭 [Architect] 次の航路を計算中...")
        response_text = self._call_llm(prompt)
        
        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
                
            proposal = json.loads(cleaned_text.strip())
            return proposal
        except json.JSONDecodeError:
            log.error("❌ [Architect] 提案のJSONパースに失敗しました。\nレスポンス: %s", response_text)
            return {
                "next_goal": "JSONパースエラーのため提案不可", 
                "expected_artifacts": [], 
                "risks": "LLMの出力フォーマット異常"
            }

    # ------------------------------------------------------------------
    # Context & External Research Methods
    # ------------------------------------------------------------------

    def _research_external_knowledge(self, goal: str) -> str:
        research_prompt = (
            "【⚠️ IMPORTANT OVERRIDE】\n"
            "This is a special sub-task. IGNORE your standard output format (TARGET_FILES, TASKS, etc.).\n"
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
            "【⚠️ IMPORTANT OVERRIDE】\n"
            "This is a special sub-task. IGNORE your standard output format (TARGET_FILES, TASKS, etc.).\n"
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
    # Parser Logic
    # ------------------------------------------------------------------

    def _parse_response(self, response: str, *, goal: str, task_id: str, search_results: str = "") -> PlanPayload:
        """LLMの回答をパースしてPlanPayloadを生成。"""
        t_files = self._extract_list(response, "TARGET_FILES")
        constraints = self._extract_list(response, "CONSTRAINTS", ["Python 3.11+"])
        acceptance = self._extract_list(response, "ACCEPTANCE", ["Passes tests"])

        # ファイル名のみにクリーンアップ
        t_files = [Path(f).name for f in t_files if f]
        if not t_files:
            t_files = [f"output_{task_id[:8]}.py"]

        tasks = self._parse_tasks(response)
        test_code = self._parse_test_code(response)

        if test_code:
            log.info("🧪 [Architect] TDD用のテストコード雛形を抽出しました。")

        return PlanPayload(
            goal=goal,
            spec_path="specs/design_spec.md",
            target_files=t_files,
            constraints=constraints,
            acceptance_criteria=acceptance,
            search_results=search_results,
            tasks=tasks,
            test_code=test_code
        )

    def _parse_tasks(self, response: str) -> list[SubTask]:
        """SubTaskセクションのパース。"""
        tasks = []
        match = re.search(r'TASKS:\s*(.*?)(?:\n\n|\Z)', response, re.S | re.I)
        if not match: return tasks
        for line in match.group(1).strip().split('\n'):
            if not line.strip().startswith('-'): continue
            d = {}
            for p in line.strip('- ').split('|'):
                if ':' in p:
                    k, v = p.split(':', 1)
                    data_key = k.strip().upper()
                    d[data_key] = v.strip()
            if 'ID' in d and 'TITLE' in d:
                deps = [x.strip() for x in d.get('DEPENDS', '').split(',') if x.strip() and x.lower() != 'none']
                tasks.append(SubTask(
                    id=d['ID'], title=d['TITLE'], description=d.get('DESC', ''), dependencies=deps
                ))
        return tasks

    def _parse_test_code(self, response: str) -> str:
        """TEST_CODEセクションからコードを抽出。"""
        bt3 = chr(96) * 3
        # 正規表現を分割してバッククォート衝突を回避
        pattern = fr'TEST_CODE:\s*{bt3}(?:python)?\s*(.*?)\s*{bt3}'
        match = re.search(pattern, response, re.S | re.I)
        if match:
            return match.group(1).strip()
        # ブロックがない場合のフォールバック
        fb = re.search(r'TEST_CODE:\s*(.*?)(?:\n\n[A-Z_]+:|\Z)', response, re.S | re.I)
        return fb.group(1).strip() if fb else ""

    @staticmethod
    def _extract_list(text: str, key: str, default: list[str] = None) -> list[str]:
        if default is None: default = []
        # 改行があってもマッチするように行単位で抽出
        match = re.search(rf"^{key}\s*:\s*(.+)$", text, re.M | re.I)
        if not match: return default
        items = [i.strip().replace("`", "") for i in match.group(1).split(",") if i.strip()]
        return items if items else default