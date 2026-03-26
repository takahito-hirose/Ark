"""
ARK (Autonomous Resilient Kernel) — LLM Provider Definitions
=============================================================
Phase 10.9: The Treasury Update
LiteLLM をベースにした「ユニバーサル・プロバイダー」により、
Gemini, Claude, DeepSeek, Ollama など全てのモデルを単一のインターフェースで統括します。
同時に、APIコスト（USD）とトークン使用量を累計で算出します。
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any

try:
    from litellm import completion, completion_cost
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

log = logging.getLogger("ARK.Providers")


# ---------------------------------------------------------------------------
# BaseProvider — 抽象基底クラス
# ---------------------------------------------------------------------------

class BaseProvider(ABC):
    """すべてのLLMプロバイダーが実装すべき共通インターフェース。"""

    def __init__(self) -> None:
        # The Treasury 用の累計カウンター
        self.session_tokens: int = 0
        self.session_cost: float = 0.0

    def generate(self, prompt: str) -> str:
        """プロンプトをLLMに送信し、テキスト応答を返す（互換性用）。"""
        text, _ = self.generate_with_usage(prompt)
        return text

    @abstractmethod
    def generate_with_usage(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """
        プロンプトをLLMに送信し、テキスト応答と使用量（トークン＆コスト）を返す。
        戻り値の usage 辞書には以下を含めること:
        - total_tokens (int): 消費トークン数
        - cost_usd (float): 推定コスト（USD）
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


# ---------------------------------------------------------------------------
# UniversalProvider (LiteLLM Wrapper)
# ---------------------------------------------------------------------------

class UniversalProvider(BaseProvider):
    """
    LiteLLM を活用し、あらゆるSOTAモデルやローカルモデルを単一のロジックで呼び出すプロバイダー
    """

    def __init__(self, model_name: str, api_key: str = "", api_base: str = "") -> None:
        super().__init__()
        if not LITELLM_AVAILABLE:
            raise RuntimeError("UniversalProvider を使うには `pip install litellm` が必要です。")

        self._model_name = model_name
        self._api_key = api_key
        self._api_base = api_base
        
        # Ollama (ローカル) の場合のエンドポイント調整
        if "ollama" in model_name.lower() or api_base:
            if not self._model_name.startswith("ollama/"):
                self._model_name = f"ollama/{self._model_name}"
            self._api_base = api_base or os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")

        # モードという概念を排除し、フラットにモデル名のみをログ出力
        log.info(f"[UniversalProvider] Ready: {self._model_name}")

    def generate_with_usage(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        log.debug(f"UniversalProvider calling... (model={self._model_name})")

        messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": self._model_name,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 8192,
        }

        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._api_base:
            kwargs["api_base"] = self._api_base

        try:
            # LiteLLM で統一された API コール
            response = completion(**kwargs)
            
            result_text = response.choices[0].message.content or ""
            
            # トークン＆コスト計算
            usage = response.usage.model_dump() if hasattr(response, 'usage') else {}
            total_tokens = usage.get("total_tokens", 0)
            
            cost_usd = 0.0
            if "ollama" not in self._model_name:
                try:
                    cost_usd = completion_cost(completion_response=response)
                except Exception as e:
                    log.debug(f"コスト計算スキップ: {e}")

            # セッションの累計に加算
            self.session_tokens += total_tokens
            self.session_cost += cost_usd

            usage_stats = {
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "model": self._model_name
            }
            
            # 実行結果のログもフラットに事実のみを出力
            if cost_usd > 0:
                log.info(f"[{self._model_name}] Tokens: {total_tokens} | Cost: ${cost_usd:.5f} (Total Session: ${self.session_cost:.5f})")
            else:
                log.info(f"[{self._model_name}] Tokens: {total_tokens} | Cost: $0.00")

            return result_text, usage_stats

        except Exception as exc:
            log.error(f"UniversalProvider generation failed: {exc}")
            raise RuntimeError(f"UniversalProvider({self._model_name}) エラー: {exc}") from exc

    def __repr__(self) -> str:
        return f"<UniversalProvider model={self._model_name!r} cost=${self.session_cost:.5f}>"


# ---------------------------------------------------------------------------
# MockProvider (テスト・オフライン用)
# ---------------------------------------------------------------------------

class MockProvider(BaseProvider):
    """接続不要のダミープロバイダー。"""

    def __init__(self, response_template: Optional[str] = None) -> None:
        super().__init__()
        self.template = response_template 
        log.debug("MockProvider initialized")

    def generate_with_usage(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        display_prompt = prompt if len(prompt) <= 100 else prompt[:100] + "..."
        estimated_tokens = len(prompt) // 4
        
        self.session_tokens += estimated_tokens
        
        usage = {"total_tokens": estimated_tokens, "cost_usd": 0.0}
        
        if self.template:
            return self.template.replace("{prompt}", display_prompt), usage

        if "REVIEW" in prompt.upper() or "STATUS" in prompt.lower():
            if "RETRY: 0" in prompt.upper() or "RETRY=0" in prompt.upper():
                return '{"status": "FAIL", "score": 0.4, "summary": "Found issues", "issues": ["Lack of docstrings"]}', usage
            return '{"status": "PASS", "score": 1.0, "summary": "Perfect!", "issues": []}', usage

        if "PLAN" in prompt.upper():
            return '{"reasoning": "Mock plan", "target_files": ["hello.py"], "tasks": [], "acceptance_criteria": [], "constraints": []}', usage

        if "CODE" in prompt.upper():
            return "``" + "`python\nprint('hello')\n``" + "`", usage

        return f"[MOCK RESPONSE] Default for: {display_prompt}", usage