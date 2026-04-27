"""
ARK (Autonomous Resilient Kernel) — LLM Provider Definitions
=============================================================
Phase 10.9: The Treasury Update (LiteLLM Enhanced)
LiteLLM をベースにした「ユニバーサル・プロバイダー」により、
Gemini, Claude, DeepSeek, Ollama など全てのモデルを単一のインターフェースで統括します。
同時に、APIコスト（USD）とトークン使用量を極めて正確に算出します。
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any

try:
    import litellm
    from litellm import completion, completion_cost
    LITELLM_AVAILABLE = True

    # 🌟 ARKのレジリエンス（回復力）を極大化する最強設定
    litellm.num_retries = 3          # 503エラーが出ても3回まで自動で粘る！
    litellm.backoff_factor = 1.5     # リトライ間隔を徐々に伸ばしてサーバーを気遣うよ！
    litellm.api_version = "v1beta"   # 404エラーを回避して最新モデル（Gemini 3）を掴む！
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
        - prompt_tokens (int): 入力トークン数
        - completion_tokens (int): 出力トークン数
        - total_tokens (int): 消費トークン数合計
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
        
        # 🌟 モデルに合わせて Temperature を賢く切り替えるよ！
        # Gemini 3系は1.0未満だと無限ループの危険があるから1.0に固定！
        temp = 1.0 if "gemini-3" in self._model_name.lower() else 0.2
        if "gemini-3" in self._model_name.lower():
            log.debug(f"Gemini 3 detected. Adjusting temperature to {temp} to prevent degraded reasoning.")

        kwargs = {
            "model": self._model_name,
            "messages": messages,
            "temperature": temp,
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
            
            # 🌟 トークン内訳の抽出を強化
            usage = response.usage.model_dump() if hasattr(response, 'usage') and response.usage else {}
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            cost_usd = 0.0
            # ローカルモデル（Ollama等）以外ならコスト計算を実行
            if "ollama" not in self._model_name.lower() and "local" not in self._model_name.lower():
                try:
                    # LiteLLMの神機能: これ一発で正確なコストが算出される
                    cost_usd = completion_cost(completion_response=response)
                except Exception as e:
                    # 未対応モデルなどで計算失敗した場合はWarningを出して0.0ドル扱いにする
                    log.warning(f"⚠️ [LiteLLM] {self._model_name} のコスト計算に失敗しました（未対応モデルの可能性）: {e}")

            # セッションの累計に加算
            self.session_tokens += total_tokens
            self.session_cost += cost_usd

            usage_stats = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "model": self._model_name
            }
            
            # 実行結果のログ（内訳も表示）
            if cost_usd > 0:
                log.info(f"[{self._model_name}] Tokens: {total_tokens} (In:{prompt_tokens}/Out:{completion_tokens}) | Cost: ${cost_usd:.5f} (Total Session: ${self.session_cost:.5f})")
            else:
                log.info(f"[{self._model_name}] Tokens: {total_tokens} (In:{prompt_tokens}/Out:{completion_tokens}) | Cost: $0.00")

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
        
        usage = {
            "prompt_tokens": estimated_tokens,
            "completion_tokens": 0,
            "total_tokens": estimated_tokens, 
            "cost_usd": 0.0,
            "model": "mock"
        }
        
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