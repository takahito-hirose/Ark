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
from typing import Optional

log = logging.getLogger("ARK.Providers")


# ---------------------------------------------------------------------------
# BaseProvider — 抽象基底クラス
# ---------------------------------------------------------------------------

class BaseProvider(ABC):
    """すべてのLLMプロバイダーが実装すべき共通インターフェース。

    Subclasses must implement :meth:`generate`.
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """プロンプトをLLMに送信し、テキスト応答を返す。

        Parameters
        ----------
        prompt:
            LLMに送るプロンプト文字列。

        Returns
        -------
        str
            LLMが生成したテキスト応答。

        Raises
        ------
        RuntimeError
            プロバイダーへの接続または生成に失敗した場合。
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------

class OllamaProvider(BaseProvider):
    """ローカル Ollama サーバーを使用するプロバイダー。

    既存の :class:`~src.core.ollama_client.OllamaClient` をラップし、
    :class:`BaseProvider` インターフェースに準拠させる。

    Parameters
    ----------
    api_endpoint:
        Ollama API のベースURL (例: ``http://localhost:11434``)。
    model_name:
        使用するモデル名 (例: ``deepseek-coder-v2``)。
    """

    def __init__(self, api_endpoint: str, model_name: str) -> None:
        from src.core.ollama_client import OllamaClient
        self._client = OllamaClient(api_endpoint=api_endpoint, model_name=model_name)
        self._model_name = model_name
        self._api_endpoint = api_endpoint
        log.debug("OllamaProvider initialized: endpoint=%s model=%s", api_endpoint, model_name)

    def generate(self, prompt: str) -> str:
        """Ollama APIにプロンプトを送信し、応答テキストを返す。

        Parameters
        ----------
        prompt:
            送信するプロンプト文字列。

        Returns
        -------
        str
            Ollamaが生成したテキスト。

        Raises
        ------
        RuntimeError
            Ollama接続またはレスポンス取得に失敗した場合。
        """
        log.debug("OllamaProvider.generate() called (model=%s)", self._model_name)
        result: Optional[str] = self._client.generate_text(prompt)
        if result is None:
            raise RuntimeError(
                f"OllamaProvider: レスポンスの取得に失敗しました。"
                f" endpoint={self._api_endpoint}, model={self._model_name}"
            )
        return result

    def __repr__(self) -> str:
        return f"<OllamaProvider model={self._model_name!r} endpoint={self._api_endpoint!r}>"


# ---------------------------------------------------------------------------
# MockProvider
# ---------------------------------------------------------------------------

class MockProvider(BaseProvider):
    """接続不要のダミープロバイダー。
    入力プロンプトのキーワードに応じて、適切な構造化データ(JSON/Markdown)を返す。
    """

    def __init__(self, response_template: Optional[str] = None) -> None:
        # 互換性のために残すが、基本は generate 内で分岐させる
        self._template = response_template 
        log.debug("MockProvider initialized (Context-Aware Mode)")

    def generate(self, prompt: str) -> str:
        """プロンプトの内容を読み取り、フェーズに応じたダミー回答を生成する。"""
        log.info("MockProvider.generate() called — generating contextual response")

        if self._template:
            return self._template.format(prompt=prompt)

        # 1. PLANNING (Architect) への回答
        if "PLANNING" in prompt or "PlanPayload" in prompt:
            return (
                '{"reasoning": "Mock planning executed.", '
                '"tasks": [{"task_id": "T1", "description": "Implement hello logic", "estimated_effort": "1h"}]}'
            )

        # 2. CODING (Coder) への回答
        if "CODING" in prompt or "CodePayload" in prompt:
            # 抽出ロジックを通すために、必ずバッククォートのブロックを含めるのが「本質」
            return (
                "I have written the code as requested.\n\n"
                "```python\n"
                "def hello():\n"
                "    print('Hello from ARK Modular Mock!')\n"
                "```"
            )

        # 3. REVIEWING (Reviewer) への回答
        if "REVIEWING" in prompt or "ReviewPayload" in prompt:
            # テストコードの期待値に合わせるため、retry回数で挙動を変える「焦らしプレイ」
            # プロンプトの中に "retry: 0" または "retry=0" が含まれているかチェック
            if "retry: 0" in prompt or "retry=0" in prompt:
                return (
                    '{"status": "FAIL", "score": 0.5, "summary": "Needs improvement", '
                    '"issues": ["Code is too simple", "Missing docstrings"]}'
                )
            # retryが1以上のときは PASS を返す
            return '{"status": "PASS", "score": 1.0, "summary": "Perfect!", "issues": []}'

        # 4. デフォルト（どれにも当てはまらない場合）
        return f"[MOCK RESPONSE] Default response for: {prompt[:50]}"


# ---------------------------------------------------------------------------
# GeminiProvider (雛形)
# ---------------------------------------------------------------------------
# --- src/core/providers.py の GeminiProvider セクションを以下に差し替え ---

class GeminiProvider(BaseProvider):
    """Google Gemini API を使用するプロバイダー（重量課金・爆速チューニング版）。"""

    def __init__(self, api_key: str = "", model_name: str = "gemini-3-flash") -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._model = None

        if not self._api_key:
            import os
            self._api_key = os.environ.get("GOOGLE_API_KEY", "")

        # 課金枠パワーをフル活用するための設定
        self._generation_config = {
            "temperature": 0.2,       # コード生成なので少し低めにして正確性をアップ
            "top_p": 0.95,
            "max_output_tokens": 8192, # 1024から一気に8倍へ！長文コードも怖くないわ
        }

        log.debug("GeminiProvider (Paid Mode) initialized: model=%s", model_name)

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

    def generate(self, prompt: str) -> str:
        self._ensure_initialized()
        log.debug("GeminiProvider.generate() calling (no-sleep mode)...")

        try:
            # 課金枠なら time.sleep(4) なんて不要！そのまま突っ込むわよ！
            response = self._model.generate_content(prompt)
            
            if not response.text:
                log.warning("GeminiProvider: 空のレスポンスが返されました。")
                return ""
                
            return response.text
        except Exception as exc:
            log.error("GeminiProvider generation failed: %s", exc)
            raise RuntimeError(f"GeminiProviderエラー: {exc}") from exc

    def __repr__(self) -> str:
        return f"<GeminiProvider model={self._model_name!r} mode='PAID_SPEED'>"