"""
ARK — Architect Agent (SYLPH)
==============================
設計フェーズを担当するエージェント。

責務
----
- ユーザーのゴールを分析し、 :class:`~src.core.models.PlanPayload` を生成する。
- 既存プロジェクトの場合、ファイルツリーを探索して関連ファイルの内容を読み込む（Context Gathering）。
- LLMへのプロンプトにはシステム指示（設計ロール・出力フォーマット要件）を内蔵する。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from src.agents.base_agent import BaseAgent
from src.core.agents import build_architect_prompt, get_file_tree
from src.core.models import PlanPayload
from src.tools.ast_analyzer import generate_code_outline

if TYPE_CHECKING:
    from src.core.providers import BaseProvider

log = logging.getLogger("ARK.Architect")

# ---------------------------------------------------------------------------
# ArchitectAgent
# ---------------------------------------------------------------------------

class ArchitectAgent(BaseAgent):
    """設計担当SYLPHエージェント。

    LLMにゴールを渡して設計を行い、 :class:`~src.core.models.PlanPayload` を返す。
    """

    def __init__(
        self, 
        provider: "BaseProvider", 
        workspace_path: Path | None = None,
        on_token_usage: Optional[Callable[[int], None]] = None
    ) -> None:
        super().__init__(
            provider, 
            role="architect", 
            workspace_path=workspace_path,
            on_token_usage=on_token_usage
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self, goal: str, task_id: str) -> PlanPayload:
        """ゴールを分析し :class:`~src.core.models.PlanPayload` を生成する。"""
        log.info("[Architect] Gathering context and analysing goal: %r", goal[:60])
        
        # 1. ワークスペースの構造（ファイルツリー）を取得
        tree = get_file_tree(self._workspace_path)
        
        # 🌟 ASTアナライザーで全Pythonファイルの設計図を抽出
        # (新規作成時は空になるように内部でガードをかけているわよ💋)
        blueprints = self._scan_blueprints()

        # 2. 探索フェーズ (Context Gathering)
        gathered_context = ""
        # 📄 が1つ以上ある（つまり既存プロジェクト感がある）場合のみ探索
        if tree.count("📄") >= 1:
            log.info("🔍 [Architect] 既存プロジェクトを検知。コンテキスト探索（Context Gathering）を開始します...")
            gathered_context = self._investigate_project(goal, tree)
        
        # 3. ゴールにコンテキストを注入
        enhanced_goal = goal
        if gathered_context:
            enhanced_goal += f"\n\n【🔍 事前調査で判明した関連ファイルのコード】\n{gathered_context}\n"

        # 4. 設計図 (blueprints) をプロンプトに渡してLLMを呼び出す
        prompt = build_architect_prompt(enhanced_goal, self._workspace_path, blueprints=blueprints)
        response = self._call_llm(prompt)
        
        # 5. レスポンスをパースしてPayloadを作成
        return self._parse_response(response, goal=goal, task_id=task_id)

    # ------------------------------------------------------------------
    # Context Gathering Methods
    # ------------------------------------------------------------------

    def _scan_blueprints(self) -> str:
        """ワークスペース内の主要なPythonファイルのASTアウトラインを一括抽出する"""
        # 🌟 [Fix] ワークスペースが存在しない、あるいは中身が空の場合はスキャンしない！
        # これで新規プロジェクト時の「自分自身のコードを読んで混乱する」のを防ぐわ💋
        if not self._workspace_path or not self._workspace_path.exists():
            return ""
            
        py_files = list(self._workspace_path.glob("*.py"))
        if not py_files:
            return ""

        outlines = []
        ignore_dirs = {".git", ".venv", "__pycache__", "node_modules", ".ark_memory"}
        
        # 再帰的に検索してアウトラインを生成
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
        """LLMにファイルツリーを見せ、改修のために読むべきファイルを指定させて中身を取得する。"""
        investigation_prompt = (
            "あなたはARKフレームワークのArchitect SYLPHです。\n"
            "既存のプロジェクトを改修するために、事前にどのファイルの中身を確認すべきか判断してください。\n\n"
            f"【ゴール】\n{goal}\n\n"
            f"【プロジェクト構造】\n```\n{tree}\n```\n\n"
            "【指示】\n"
            "ゴールを達成するために内容を確認する必要があるファイルを、カンマ区切りで出力してください。\n"
            "出力フォーマット: READ_FILES: path/to/file1.py, path/to/file2.py\n"
            "確認が不要な場合や、全体像から判断できる場合は READ_FILES: NONE と出力してください。"
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
                                content = content[:10000] + "\n... (truncated for context limit)"
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
    ) -> PlanPayload:
        """LLMレスポンスから :class:`~src.core.models.PlanPayload` を抽出する。"""
        
        # 1. 各項目の抽出
        target_files   = self._extract_list(response, "TARGET_FILES")
        constraints    = self._extract_list(response, "CONSTRAINTS",   ["Python 3.11+", "型ヒント必須"])
        acceptance     = self._extract_list(response, "ACCEPTANCE",    ["no syntax errors", "file exists"])

        # 🌟 [Fix] ファイル名のサニタイズ。フォルダ名が含まれていたら削ぎ落とす！
        # LLMが 'workspace/app.py' と書いても 'app.py' に変換されるわ💋
        target_files = [Path(f).name for f in target_files if f]

        # 2. 万が一ターゲットファイルが見つからなかった場合の最後の命綱
        if not target_files:
            log.warning("⚠️ [Architect] TARGET_FILES のパースに失敗したわ！レスポンスを確認してね。")
            # 応答の中からそれっぽい .py ファイルを探す
            py_matches = re.findall(r'([\w\-\.]+\.py)', response)
            if py_matches:
                target_files = [Path(m).name for m in py_matches]
            else:
                target_files = [f"output_{task_id[:8]}.py"]

        payload = PlanPayload(
            goal=goal,
            spec_path="specs/core_logic.md",
            target_files=target_files,
            constraints=constraints,
            acceptance_criteria=acceptance,
        )
        log.info(
            "[Architect] PlanPayload created: target_files=%s",
            payload.target_files,
        )
        return payload

    @staticmethod
    def _extract_list(text: str, key: str, default: list[str] | None = None) -> list[str]:
        """``KEY: value1, value2`` 形式の行をパースしてリストを返す。"""
        if default is None:
            default = []
            
        pattern = rf"^{re.escape(key)}\s*:\s*(.+)$"
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if not match:
            log.debug("Key %r not found in LLM response.", key)
            return default
            
        raw = match.group(1).strip()
        # backticks や不要な記号をクリーニング
        raw = raw.replace("`", "").strip()
        
        items = [item.strip() for item in raw.split(",") if item.strip()]
        return items if items else default