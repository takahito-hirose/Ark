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

    外部LLMへの接続を一切行わず、固定のダミー文字列を返す。
    テスト・CI環境・オフライン開発に使用する。

    Parameters
    ----------
    response_template:
        返却するレスポンスのテンプレート。
        ``{prompt}`` プレースホルダーを含む場合はプロンプトで置換される。
    """

    _DEFAULT_TEMPLATE: str = (
        "[MOCK RESPONSE] このレスポンスはMockProviderが生成したダミーです。\n"
        "Prompt受信: {prompt}\n"
        "--- 生成コード (mock) ---\n"
        "def main() -> None:\n"
        '    print("Hello from ARK MockProvider!")\n\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    )

    def __init__(self, response_template: Optional[str] = None) -> None:
        self._template = response_template or self._DEFAULT_TEMPLATE
        log.debug("MockProvider initialized")

    def generate(self, prompt: str) -> str:
        """ダミー文字列を返す。外部接続は行わない。

        Parameters
        ----------
        prompt:
            受信したプロンプト（レスポンスに埋め込まれる）。

        Returns
        -------
        str
            固定のダミーレスポンス文字列。
        """
        log.info("MockProvider.generate() called — returning dummy response")
        # promptが長い場合は先頭100文字のみ埋め込む
        short_prompt = prompt[:100] + ("..." if len(prompt) > 100 else "")
        return self._template.format(prompt=short_prompt)

    def __repr__(self) -> str:
        return "<MockProvider>"


# ---------------------------------------------------------------------------
# GeminiProvider (雛形)
# ---------------------------------------------------------------------------

class GeminiProvider(BaseProvider):
    """Google Gemini API を使用するプロバイダー。

    .. note::
        このクラスは現時点では **雛形実装** です。
        実際に使用するには ``google-generativeai`` パッケージと
        有効な API キーが必要です。

    Parameters
    ----------
    api_key:
        Google AI Studio で発行したAPIキー。
        省略時は環境変数 ``GOOGLE_API_KEY`` を参照する。
    model_name:
        使用するGeminiモデル名 (例: ``gemini-1.5-flash``)。
    """

    def __init__(self, api_key: str = "", model_name: str = "gemini-1.5-flash") -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._model = None  # 遅延初期化

        if not self._api_key:
            import os
            self._api_key = os.environ.get("GOOGLE_API_KEY", "")

        log.debug("GeminiProvider initialized: model=%s", model_name)

    def _ensure_initialized(self) -> None:
        """google-generativeaiクライアントを遅延初期化する。"""
        if self._model is not None:
            return

        try:
            import google.generativeai as genai  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "GeminiProviderを使用するには `google-generativeai` パッケージが必要です。\n"
                "インストール: pip install google-generativeai"
            ) from exc

        if not self._api_key:
            raise RuntimeError(
                "GeminiProviderを使用するには有効なAPIキーが必要です。\n"
                "config.yaml の `gemini_api_key` または環境変数 `GOOGLE_API_KEY` を設定してください。"
            )

        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel(self._model_name)
        log.info("GeminiProvider: model %r ready", self._model_name)

    def generate(self, prompt: str) -> str:
        """Gemini APIにプロンプトを送信し、応答テキストを返す。

        Parameters
        ----------
        prompt:
            送信するプロンプト文字列。

        Returns
        -------
        str
            Geminiが生成したテキスト。

        Raises
        ------
        RuntimeError
            `google-generativeai` 未インストールまたはAPIキー未設定の場合。
        """
        self._ensure_initialized()
        log.debug("GeminiProvider.generate() called (model=%s)", self._model_name)

        response = self._model.generate_content(prompt)  # type: ignore[union-attr]
        return response.text

    def __repr__(self) -> str:
        return f"<GeminiProvider model={self._model_name!r}>"
