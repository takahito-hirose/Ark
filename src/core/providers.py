
"""
ARK (Autonomous Resilient Kernel) — LLM Provider Definitions
=============================================================
Strategyパターンに基づく、マルチプロバイダー対応の基盤定義。

使用可能なプロバイダー:
- ``OllamaProvider``: ローカル Ollama サーバーを使用
- ``MockProvider``:   接続不要。テスト・オフライン環境向けダミー実装
- ``GeminiProvider``: Google Gemini API を使用（雛形）

Usage
-----
::

    from src.core.providers import MockProvider, OllamaProvider

    provider = MockProvider()
    response = provider.generate("テスト用プロンプト")
    print(response)  # "[MOCK] ..."
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any

log = logging.getLogger("ARK.Providers")


# ---------------------------------------------------------------------------
# BaseProvider — 抽象基底クラス
# ---------------------------------------------------------------------------

class BaseProvider(ABC):
    """すべてのLLMプロバイダーが実装すべき共通インターフェース。"""

    # 🌟 ここがポイント！抽象メソッドじゃないから、各プロバイダで書かなくてOK！
    def generate(self, prompt: str) -> str:
        """プロンプトをLLMに送信し、テキスト応答を返す（互換性用）。"""
        text, _ = self.generate_with_usage(prompt)
        return text

    # 🌟 各プロバイダは、この「テキストと使用量を返す」メソッドだけ作ればOK！
    @abstractmethod
    def generate_with_usage(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """プロンプトをLLMに送信し、テキスト応答とトークン使用量を返す。"""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------

class OllamaProvider(BaseProvider):
    """ローカル Ollama サーバーを使用するプロバイダー。"""

    def __init__(self, api_endpoint: str, model_name: str) -> None:
        from src.core.ollama_client import OllamaClient
        self._client = OllamaClient(api_endpoint=api_endpoint, model_name=model_name)
        self._model_name = model_name
        self._api_endpoint = api_endpoint
        log.debug("OllamaProvider initialized: endpoint=%s model=%s", api_endpoint, model_name)

    def generate_with_usage(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        log.debug("OllamaProvider.generate_with_usage() called (model=%s)", self._model_name)
        result, usage = self._client.generate_text(prompt)
        if result is None:
            raise RuntimeError(
                f"OllamaProvider: レスポンスの取得に失敗しました。"
                f" endpoint={self._api_endpoint}, model={self._model_name}"
            )
        return result, usage

    def __repr__(self) -> str:
        return f"<OllamaProvider model={self._model_name!r} endpoint={self._api_endpoint!r}>"


# ---------------------------------------------------------------------------
# MockProvider
# ---------------------------------------------------------------------------

class MockProvider(BaseProvider):
    """接続不要のダミープロバイダー。"""

    def __init__(self, response_template: Optional[str] = None) -> None:
        self.template = response_template 
        log.debug("MockProvider initialized (Context-Aware Mode)")

    def generate_with_usage(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        display_prompt = prompt if len(prompt) <= 100 else prompt[:100] + "..."
        estimated_tokens = len(prompt) // 4
        
        if self.template:
            return self.template.replace("{prompt}", display_prompt), {"total_tokens": estimated_tokens}

        if "REVIEW" in prompt.upper() or "STATUS" in prompt.lower():
            if "RETRY: 0" in prompt.upper() or "RETRY=0" in prompt.upper():
                return '{"status": "FAIL", "score": 0.4, "summary": "Found issues", "issues": ["Lack of docstrings"]}', {"total_tokens": 50}
            return '{"status": "PASS", "score": 1.0, "summary": "Perfect!", "issues": []}', {"total_tokens": 30}

        if "PLAN" in prompt.upper():
            return '{"reasoning": "Mock plan", "target_files": ["hello.py"], "tasks": [], "acceptance_criteria": [], "constraints": []}', {"total_tokens": 100}

        if "CODE" in prompt.upper():
            # マークダウンの記号で表示システムが勘違いしないように分割結合の裏技を使うわ！💋
            return "``" + "`python\nprint('hello')\n``" + "`", {"total_tokens": 70}

        return f"[MOCK RESPONSE] Default for: {display_prompt}", {"total_tokens": estimated_tokens}


# ---------------------------------------------------------------------------
# GeminiProvider
# ---------------------------------------------------------------------------

class GeminiProvider(BaseProvider):
    """Google Gemini API を使用するプロバイダー。"""

    def __init__(self, api_key: str = "", model_name: str = "gemini-3-flash") -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._model = None

        if not self._api_key:
            import os
            self._api_key = os.environ.get("GOOGLE_API_KEY", "")

        self._generation_config = {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_output_tokens": 8192,
        }

        log.debug("GeminiProvider initialized: model=%s", model_name)

    def _ensure_initialized(self) -> None:
        if self._model is not None:
            return

        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError("pip install google-generativeai を実行してね！") from exc

        if not self._api_key:
            raise RuntimeError("APIキーが見つからないわ！.envを確認して？")

        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel(
            model_name=self._model_name,
            generation_config=self._generation_config
        )
        log.info("GeminiProvider: Paid Tier Model %r Ready 🚀", self._model_name)

    def generate_with_usage(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        self._ensure_initialized()
        log.debug("GeminiProvider.generate_with_usage() calling...")

        try:
            response = self._model.generate_content(prompt)
            
            if not response.text:
                log.warning("GeminiProvider: 空のレスポンスが返されました。")
                return "", {"total_tokens": 0}
            
            estimated_tokens = (len(prompt) + len(response.text)) // 4
            usage = {"total_tokens": estimated_tokens}
            
            return response.text, usage
        except Exception as exc:
            log.error("GeminiProvider generation failed: %s", exc)
            raise RuntimeError(f"GeminiProviderエラー: {exc}") from exc

    def __repr__(self) -> str:
        return f"<GeminiProvider model={self._model_name!r} mode=\'PAID_SPEED\'>"