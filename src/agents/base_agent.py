"""
ARK — Base Agent (Grand Foundation / Phase 16.5 Neuro-Link Edition)
======================================================
すべての SYLPH エージェントが継承する抽象基底クラス。
スキルの動的ロード、自律記憶の引き出し（Dynamic RAG）、LLM 呼び出し、
そして「思考のストリーミング（Neuro-Link）」を管理するわ！
"""

from __future__ import annotations

import logging
import re
from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from src.core.providers import BaseProvider
    from src.memory.memory_manager import MemoryManager

log = logging.getLogger("ARK.Agent")

class BaseAgent(ABC):
    def __init__(
        self, 
        provider: "BaseProvider", 
        role: str = "agent", 
        workspace_path: Path | str | None = None,
        on_token_usage: Optional[Callable[[int], None]] = None,
        on_thought: Optional[Callable[[str, str, str, Optional[str]], None]] = None,
        memory_manager: Optional["MemoryManager"] = None
    ) -> None:
        self._provider = provider
        self._role     = role.lower()
        self._on_token_usage = on_token_usage
        self._on_thought = on_thought
        self._memory = memory_manager
        
        if workspace_path is None:
            self._workspace_path = Path(".")
        else:
            self._workspace_path = Path(workspace_path)
            
        # 🌟 ここで動的にスキルをロードするよ！
        self._skills_prompt = self._load_skills()
        
        log.debug("[%s] initialized with memory_manager: %s", self._role, "Ready" if self._memory else "None")

    def _load_skills(self) -> str:
        """
        プロバイダーの性質（SOTA or Local）に合わせて、最適な Skills.md を動的にロードするよ！
        """
        current_dir = Path(__file__).parent
        
        # 🌟 NEW: プロバイダーがローカルかどうかを判定
        provider_info = str(self._provider).lower()
        is_local = "ollama" in provider_info or "local" in provider_info

        # 読み込むファイル名を決定
        filename = "Skills_local.md" if is_local else "Skills.md"
        skills_path = current_dir / self._role / filename
        
        # フォールバック処理（ローカル用ファイルがまだ作られていない場合は通常版を読む）
        if not skills_path.exists() and is_local:
            log.warning("[%s] ⚠️ %s が見つからないから、標準の Skills.md にフォールバックするね！", self._role, filename)
            skills_path = current_dir / self._role / "Skills.md"
        
        try:
            if skills_path.exists():
                with open(skills_path, "r", encoding="utf-8") as f:
                    log.info("[%s] 📖 %s をロードしたよ！（Local-Mode: %s）", self._role, skills_path.name, is_local)
                    return f.read()
            else:
                log.warning("[%s] ⚠️ スキルファイルがないから、デフォルト人格でいくね！", self._role)
                return f"You are an expert {self._role.capitalize()}."
        except Exception as e:
            log.error("[%s] ❌ Skillsの読み込みエラー: %s", self._role, e)
            return f"You are an expert {self._role.capitalize()}."

    # ------------------------------------------------------------------
    # 共通 LLM 呼び出しラッパー (Dynamic RAG & Neuro-Link 搭載)
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str, task_name: str = "Mission Execution") -> str:
        """
        プロバイダーを呼び出す前に自律的に過去の「教訓」を思い出し、
        レスポンスから思考プロセスを抽出してHUDにストリーミングするよ！
        """
        log.info("[%s] Calling LLM (%r) …", self._role, self._provider)
        
        # 🧠 過去の教訓をアーカイブから検索
        relevant_memories = ""
        if self._memory:
            log.info("[%s] 🧠 過去の教訓をアーカイブから検索中...", self._role)
            relevant_memories = self._memory.recall_memory(prompt, role=self._role, n_results=3)
            
            if relevant_memories:
                log.info("[%s] 💡 関連する記憶が見つかったよ！プロンプトに注入するね！", self._role)

        # プロンプトの3層合体（人格 + 経験 + タスク）
        full_prompt = f"{self._skills_prompt}\n{relevant_memories}\n\n### Current Task:\n{prompt}"
        
        try:
            response, usage = self._provider.generate_with_usage(full_prompt)
            
            if self._on_token_usage:
                estimated_tokens = (len(full_prompt) + len(response)) // 4
                actual_tokens = usage.get("total_tokens", estimated_tokens) if usage else estimated_tokens
                self._on_token_usage(actual_tokens)

            # Neuro-Link 思考ストリーミング処理
            thought_match = re.search(r"<thought>(.*?)</thought>", response, re.DOTALL | re.IGNORECASE)
            if thought_match:
                thought_text = thought_match.group(1).strip()
                log.info("[%s] 💬 思考プロセスをキャッチ！ HUDへストリーミングするよ！", self._role)
                
                if self._on_thought:
                    self._on_thought(self._role.capitalize(), task_name, thought_text, None)

            return response

        except Exception as exc:
            log.warning("[%s] ⚠️ LLM call failed: %s", self._role, exc)
            return ""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} role={self._role!r} provider={self._provider!r}>"