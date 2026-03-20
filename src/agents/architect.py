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
        
        # 1. ワークスペースの構造（ファイルツリー）を取得 (coreの関数を使用💋)
        tree = get_file_tree(self._workspace_path)
        
        # 2. 探索フェーズ (Context Gathering)
        gathered_context = ""
        # 📄 が2つ以上ある（つまり既存プロジェクト感がある）場合のみ探索
        if tree.count("📄") >= 1:
            log.info("🔍 [Architect] 既存プロジェクトを検知。コンテキスト探索（Context Gathering）を開始します...")
            gathered_context = self._investigate_project(goal, tree)
        
        # 3. ゴールにコンテキストを注入（ツリー構造は build_architect_prompt で付与されるのでここでは付けない）
        enhanced_goal = goal
        if gathered_context:
            enhanced_goal += f"\n\n【🔍 事前調査で判明した関連ファイルのコード】\n{gathered_context}\n"

        # src/core/agents.py のロジックを使用してプロンプトを構築
        prompt = build_architect_prompt(enhanced_goal, self._workspace_path)
        response = self._call_llm(prompt)
        
        # payload生成時には、ログ等が汚れないように元の goal を渡す
        return self._parse_response(response, goal=goal, task_id=task_id)

    # ------------------------------------------------------------------
    # Context Gathering Methods
    # ------------------------------------------------------------------

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
        
        # READ_FILES: をパースするわよ💋
        pattern = r"READ_FILES\s*:\s*(.+)"
        match = re.search(pattern, response, re.IGNORECASE)
        context_parts = []
        
        if match:
            files_str = match.group(1).strip()
            if files_str.upper() != "NONE":
                # 絵文字や余計な文字が混ざった時のためのクレンジング
                clean_files = [f.strip().replace("📄", "").replace("📁", "").strip() for f in files_str.split(",")]
                
                for fp in clean_files:
                    if not fp: continue
                    target_file = self._workspace_path / fp
                    if target_file.is_file():
                        try:
                            # ファイルを読み込む
                            content = target_file.read_text(encoding="utf-8")
                            # 長すぎる場合はトークン節約のために切り詰める（約1万文字でカット）
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
        
        # デフォルトを「勝手な新規ファイル」にするのをやめたわ！
        # もしパースに失敗したら、とりあえずレスポンスの中のそれっぽいファイル名を探すか、フォールバックとしてNoneを返すようにする。
        # （ここでは空リストにすると後続の処理で死ぬかもしれないから、最低限のフォールバックは残すけど、極力LLMの出力を信じるわ💋）
        
        target_files   = self._extract_list(response, "TARGET_FILES")
        constraints    = self._extract_list(response, "CONSTRAINTS",   ["Python 3.11+", "型ヒント必須"])
        acceptance     = self._extract_list(response, "ACCEPTANCE",    ["no syntax errors", "file exists"])

        # 万が一ターゲットファイルが見つからなかった場合の最後の命綱
        if not target_files:
            log.warning("⚠️ [Architect] TARGET_FILES のパースに失敗したわ！レスポンスを確認してね。")
            target_files = [f"workspace/output_{task_id[:8]}.py"]

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